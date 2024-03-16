import os
import asyncio
from datetime import datetime
import logging

import discord
from colorama import Fore, Style

from db_handler import MemberTaggerDBHandler as DBHandler
from components.embeds import EmbedHandler
from components.views import TagMemberView1, UntagMemberView1, GetTaggedPostsView, GetTaggedMembersView


# TODO: DBのローカル化(sqlite3, mysql ...)？
# TODO: 毎日規定の時間にタグ付けされたメンバーに通知を送る機能
# TODO: 通知のON/OFF機能
# TODO: loggingのhandlerを設定する
# TODO: pingのembedをEmbedHandlerで作成するようにする
# TODO: 可能ならば、untagのmember_selectで、tagされているメンバーのみを表示するようにする
# TODO: embedにおけるエラーハンドリング、エラーメッセージの表示をより詳細にする


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

intents = discord.Intents.all()
handler = DBHandler()

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
    
    async def sync_commands(self):
        if self.synced:
            return
        await tree.sync()
        self.synced = True
    
    async def set_presence(self):
        await self.change_presence(activity=discord.CustomActivity(name='/help', type=discord.ActivityType.listening))
    
    async def keep_alive(self):
        # 10分ごとにpingを送信(presenceの更新)
        await self.wait_until_ready()
        while not self.is_closed():
            await self.change_presence(activity=discord.CustomActivity(name='/help', type=discord.ActivityType.listening))
            now = datetime.now().strftime('%Y/%m/%d, %H:%M:%S')
            logging.info(Fore.GREEN + f'Pinged at {now}' + Style.RESET_ALL)
            await asyncio.sleep(120)

client = Client()
tree = discord.app_commands.CommandTree(client)

async def called_logger(command_name: str, interaction: discord.Interaction):
    command_name = Fore.YELLOW + command_name + Style.RESET_ALL
    user_name = Fore.BLUE + str(interaction.user.name) + Style.RESET_ALL
    user_id = Fore.BLUE + str(interaction.user.id) + Style.RESET_ALL
    time = Fore.MAGENTA + datetime.now().strftime("%Y/%m/%d, %H:%M:%S") + Style.RESET_ALL
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
    await interaction.response.send_message(ephemeral=True, view=TagMemberView1(), embed=EmbedHandler(step=1, mode='tag').get_embed())

@tree.command(name="untag", description="投稿からメンバーのタグ付けを外します")
async def untag_member_command(interaction: discord.Interaction):
    await called_logger('untag', interaction)
    await interaction.response.send_message(ephemeral=True, view=UntagMemberView1(), embed=EmbedHandler(step=1, mode='untag').get_embed())

@tree.command(name="tagged_posts", description="メンバーがタグ付けされている投稿を表示します")
async def get_tagged_posts_command(interaction: discord.Interaction):
    await called_logger('tagged_posts', interaction)
    await interaction.response.send_message(ephemeral=True, view=GetTaggedPostsView(), embed=EmbedHandler(step=1, mode='get_tagged_posts').get_embed())

@tree.command(name="tagged_members", description="スレッドにタグ付けされているメンバーを表示します")
async def get_tagged_members_command(interaction: discord.Interaction):
    await called_logger('tagged_members', interaction)
    await interaction.response.send_message(ephemeral=True, view=GetTaggedMembersView(), embed=EmbedHandler(step=1, mode='get_tagged_members').get_embed())

secret_token = str(os.getenv('DISCORD_BOT_TOKEN_MT'))
client.run(secret_token)