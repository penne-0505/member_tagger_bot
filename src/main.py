import os
import asyncio
import datetime
import logging

import discord
from colorama import Fore, Style

from db_handler import MemberTaggerDBHandler, MemberTaggerNotifyDBHandler
from components.embeds import EmbedHandler
from components.views import TagMemberView1, UntagMemberView1, GetTaggedthreadsView, GetTaggedMembersView


# TODO: DBのローカル化(sqlite3, mysql ...)？
# __TODO: 毎日規定の時間にタグ付けされたメンバーに通知を送る機能
# __TODO: 通知のON/OFF機能
# TODO: loggingのhandlerを設定する
# TODO: pingのembedをEmbedHandlerで作成するようにする
# TODO: 可能ならば、untagのmember_selectで、tagされているメンバーのみを表示するようにする
# TODO: embedにおけるエラーハンドリング、エラーメッセージの表示をより詳細にする
# TODO: コメント、docstringの充実化


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

intents = discord.Intents.all()
handler = MemberTaggerDBHandler()

class NotifyHandler:
    # threadsを取得 -> 通知を送信する時間を決定する -> 送信時間まで待機 -> thread_idsをthreadに変換 -> threadに紐づけられていたmember(dict内)に対して通知を送る
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.notify_db_handler = MemberTaggerNotifyDBHandler()
    
    async def notify(self, target_members: dict[str, dict[discord.Thread, datetime.datetime]], until: int = None):
        
        for member_id, threads in target_members.items():
            member = self.interaction.guild.get_member(int(member_id))
            embed = discord.Embed(
                title='',
                description='',
                color=discord.Color.yellow()
            )
            if member:
                members = []
                for thread, deadline in threads.items():
                    embed.title = f'提出まで残り{str((deadline - datetime.datetime.now()).days)}日です！'
                    members.append(f'・ {thread.mention}')
                embed.description = '\n'.join(members)
                embed.color = discord.Color.yellow() if 0 < until <= 5 else discord.Color.red()
                await thread.send(embed=embed)
            else:
                logging.warning(f'Member {member_id} not found')
    
    async def wait_until_notify(self):
        while True:
            # threadsと現在時刻を取得
            threads = self.get_threads([self.interaction.guild.get_thread(int(member_id)) for member_id in self.notify_db_handler.get_notify_validity_members()], self.interaction)
            now = datetime.datetime.now()
            # thread内のdeadlineが5, 3, 1, 0日前のものを取得
            prior_notify_5days = {member_id: {thread: deadline for thread, deadline in threads[member_id].items() if (deadline - now).days == 5} for member_id in threads}
            prior_notify_3days = {member_id: {thread: deadline for thread, deadline in threads[member_id].items() if (deadline - now).days == 3} for member_id in threads}
            prior_notify_1day = {member_id: {thread: deadline for thread, deadline in threads[member_id].items() if (deadline - now).days == 1} for member_id in threads}
            very_day_notify = {member_id: {thread: deadline for thread, deadline in threads[member_id].items() if (deadline - now).days == 0} for member_id in threads}
            # 昼の12時になったら、5, 3, 1日前の通知を送信
            if now.hour == 12 and now.minute == 0:
                await self.notify(prior_notify_5days)
                await self.notify(prior_notify_3days)
                await self.notify(prior_notify_1day)
            # 夜中の12(24)時になったら、当日の通知を送信
            if now.hour == 0 and now.minute == 0:
                await self.notify(very_day_notify)
            # 30分ごとに最新のthreadsを取得
            await asyncio.sleep(1800) if now.second == 0 else asyncio.sleep(1800 - now.minute * 60 - now.second)

    async def notify_member_toggle(self, members: dict[discord.Member]) -> bool:
        toggle_result = [self.notify_db_handler.toggle_notify(member.id) for member in members]
        if all(toggle_result):
            return True
        else:
            return False
    
    '''
    FIXME: 以下のエラーが発生する
    future: <Task finished name='Task-13' coro=<NotifyHandler.wait_until_notify() done, defined at /bot/src/main.py:55> exception=TypeError("'coroutine' object is not iterable")>

    Traceback (most recent call last):

    File "/bot/src/main.py", line 61, in wait_until_notify

    prior_notify_5days = {member_id: {thread: deadline for thread, deadline in threads[member_id].items() if (deadline - now).days == 5} for member_id in threads}

    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    TypeError: 'coroutine' object is not iterable

    /usr/local/lib/python3.11/asyncio/base_events.py:1937: RuntimeWarning: coroutine 'NotifyHandler.get_threads' was never awaited

    handle = None  # Needed to break cycles when an exception occurs.

    RuntimeWarning: Enable tracemalloc to get the object allocation traceback
    '''

    async def get_threads(
        self,
        target_members: list[discord.Member],
        interaction: discord.Interaction
        ) -> dict[str, dict[discord.Thread | None, datetime.datetime]]:

        thread_ids = {str(member.id): handler.get_tagged_threads(str(member.id)) for member in target_members}
        # thread_idsが空の場合はNoneを返す
        if not thread_ids.items() or not list(thread_ids.values())[0]:
            return None
        else:
            # thread_idsをthreadに変換, deadlineをdatetimeに変換
            threads = {
                member_id: {
                    interaction.guild.get_thread(int(thread_id)): datetime.datetime.strptime(deadline, "%Y-%m-%d") for thread_id, deadline in threads.items()
                    } for member_id, threads in thread_ids.items()
                }
            return threads

class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False
    
    async def on_ready(self):
        logging.info(Fore.YELLOW + 'Bot is starting...' + Style.RESET_ALL)
        logging.info(Fore.YELLOW + 'Syncing commands...' + Style.RESET_ALL)
        if not self.synced:
            await self.sync_commands()
        logging.info(Fore.GREEN + 'Commands synced' + Style.RESET_ALL)
        await self.set_presence()
        logging.info(Fore.BLUE + f'Logged in as {self.user.name} ({self.user.id})' + Style.RESET_ALL)
        logging.info(Fore.GREEN + 'Bot is ready' + Style.RESET_ALL)
        self.loop.create_task(self.keep_alive())
        logging.info(Fore.GREEN + 'Keep alive task started' + Style.RESET_ALL)
        self.loop.create_task(NotifyHandler(self).wait_until_notify())
        logging.info(Fore.GREEN + 'Notify task started' + Style.RESET_ALL)
    
    async def sync_commands(self):
        if self.synced:
            return
        await tree.sync()
        self.synced = True
    
    async def set_presence(self):
        timezone = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(timezone).strftime('%H:%M')
        await self.change_presence(
            activity=discord.Game(name=f'/help | Synced {now}')
        )
    
    async def keep_alive(self):
        # 10分ごとにpingを送信(presenceの更新)
        await self.wait_until_ready()
        while not self.is_closed():
            await self.set_presence()
            timezone = datetime.timezone(datetime.timedelta(hours=9))
            now = datetime.datetime.now(timezone).strftime('%Y/%m/%d, %H:%M:%S')
            logging.info(Fore.GREEN + f'Pinged at {now}' + Style.RESET_ALL)
            await asyncio.sleep(600)

client = Client()
tree = discord.app_commands.CommandTree(client)

async def called_logger(command_name: str, interaction: discord.Interaction):
    command_name = Fore.YELLOW + command_name + Style.RESET_ALL
    user_name = Fore.BLUE + str(interaction.user.name) + Style.RESET_ALL
    user_id = Fore.BLUE + str(interaction.user.id) + Style.RESET_ALL
    time = Fore.MAGENTA + datetime.datetime.now().strftime("%Y/%m/%d, %H:%M:%S") + Style.RESET_ALL
    logging.info(f'Command {command_name} called by {user_name} ({user_id}) at {time}')


@tree.command(name='ping', description='pong')
async def ping(interaction: discord.Interaction):
    await called_logger('ping', interaction)
    to_be_shown_data = {
        'Websocket Latency': round(client.latency * 1000),
        'Message Author': f'{interaction.user.name}',
        'Author Mention': f'{interaction.user.mention}',
        'Message Author ID': f'{interaction.user.id}',
    }
    await interaction.response.send_message(
        ephemeral=True,
        embed=discord.Embed(
            title='Pong!',
            description='\n'.join([f'**{key}**: {value}' for key, value in to_be_shown_data.items()]),
            color=discord.Color.green()
        )
    )

@tree.command(name='help', description='コマンド一覧を表示します')
async def help(interaction: discord.Interaction):
    await called_logger('help', interaction)
    commands = {command.name: command.description for command in tree.get_commands()}
    commands['ping'] = '通信や処理にかかった時間を返します'
    embed = discord.Embed(
        title='コマンド一覧',
        description='\n'.join([f'**`/{command}`** : {description}' for command, description in commands.items()]),
        color=discord.Color.blue()
    )
    await interaction.response.send_message(ephemeral=True, embed=embed)

@tree.command(name="tag", description="投稿にメンバーをタグ付けします")
async def tag_member_command(interaction: discord.Interaction):
    await called_logger('tag', interaction)
    await interaction.response.send_message(ephemeral=True, view=TagMemberView1(), embed=EmbedHandler(interaction).get_embed_tag(1))

@tree.command(name="untag", description="投稿からメンバーのタグ付けを外します")
async def untag_member_command(interaction: discord.Interaction):
    await called_logger('untag', interaction)
    await interaction.response.send_message(ephemeral=True, view=UntagMemberView1(), embed=EmbedHandler(interaction).get_embed_untag(1))

@tree.command(name="tagged_threads", description="メンバーがタグ付けされている投稿を表示します")
async def get_tagged_threads_command(interaction: discord.Interaction):
    await called_logger('tagged_threads', interaction)
    await interaction.response.send_message(ephemeral=True, view=GetTaggedthreadsView(), embed=EmbedHandler(interaction).get_embed_get_tagged_threads(1))

@tree.command(name="tagged_members", description="スレッドにタグ付けされているメンバーを表示します")
async def get_tagged_members_command(interaction: discord.Interaction):
    await called_logger('tagged_members', interaction)
    await interaction.response.send_message(ephemeral=True, view=GetTaggedMembersView(), embed=EmbedHandler(interaction).get_embed_get_tagged_members(1))

@tree.command(name='notify_toggle', description='通知のON/OFFを切り替えます')
async def notify_toggle_command(interaction: discord.Interaction):
    await called_logger('notify_toggle', interaction)
    notify_db_handler = MemberTaggerNotifyDBHandler()
    current_notify_state = notify_db_handler.get_notify_state(str(interaction.user.id))
    await interaction.response.send_message(ephemeral=True, embed=EmbedHandler(interaction).get_embed_notify_toggle(1, current_notify_state))
    del notify_db_handler

secret_token = str(os.getenv('DISCORD_BOT_TOKEN_MT'))
client.run(secret_token)