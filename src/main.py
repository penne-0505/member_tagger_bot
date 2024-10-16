import os
import asyncio
import datetime
import logging

import discord
from discord import app_commands
from discord.ext import tasks
from colorama import Fore, Style

from db_handler import MemberTaggerNotifyDBHandler
from components.embeds import EmbedHandler
from components.views import (
    TagMemberView1,
    UntagMemberView1,
    GetTaggedthreadsView,
    GetTaggedMembersView,
    NotifyToggleView,
    InviteView,
)
from notify_handler import NotifyHandler


# TODO: DBのローカル化(sqlite3, mysql ...)？(もはやjsonでもいいかも)
# TODO: コメント、docstringの充実化
# TODO: client?のloggingをオーバーライドして、ログが重複しないようにする
# TODO: permissionの適切なスコープ設定
# TODO: interactionのextrasを使って情報のやり取り出来る情報が無いか見てみる
# TODO: 全体的な処理構造を見直す(特にViewやEmbed、そこでやりとりするデータの流れ)
# TODO: delete_afterなどを使って、前日の通知が消えるようにする(そもそもdelete_afterはそんなに長期間待機出来るのか？)
# TODO: poetryでパッケージ管理


intents = discord.Intents.all()


class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False
        self.notify_handler = NotifyHandler()

    ############## discord.py events ##############

    async def on_ready(self):
        logging.info(Fore.YELLOW + "Bot is starting..." + Style.RESET_ALL)

        if not self.synced:
            await self.sync_commands()  # treeコマンドの同期
        logging.info(Fore.GREEN + "Commands synced" + Style.RESET_ALL)

        # botが参加しているguildのメンバーとDBを同期
        for guild in self.guilds:
            try:
                logging.info(
                    Fore.GREEN
                    + f"Joined guild {guild.name} ({guild.id})"
                    + Style.RESET_ALL
                )
                self.notify_handler.guild = guild
                await self.notify_handler.notify_member_db_sync()
            except discord.errors.Forbidden:
                logging.warning(
                    Fore.RED
                    + f"Failed to join guild {guild.name} ({guild.id})"
                    + Style.RESET_ALL
                )
        logging.info(
            Fore.BLUE
            + f"Logged in as {self.user.name} ({self.user.id})"
            + Style.RESET_ALL
        )

        # 10分ごとにpresenceを更新するループタスクを開始
        self.set_presence.start()

        logging.info(Fore.GREEN + Style.BRIGHT + "Bot is ready" + Style.RESET_ALL)

        ######## ここから通知タスク ########
        timezone = datetime.timezone(datetime.timedelta(hours=9))  # JST
        today = datetime.datetime.now(timezone).date()
        midnight = datetime.datetime.combine(
            today, datetime.time(0, 0), tzinfo=timezone
        )

        # 通知タスクを開始するまでの時間を計算
        time_to_notify = (
            midnight + datetime.timedelta(days=1) - datetime.datetime.now(timezone)
        )
        # 時刻を算出
        time_to_notify_dt = datetime.datetime.now(timezone) + time_to_notify

        time_to_notify_dt = (
            Fore.LIGHTMAGENTA_EX
            + datetime.datetime.strftime(time_to_notify_dt, "%Y/%m/%d %H:%M:%S")
            + Style.RESET_ALL
            + Fore.GREEN
        )
        logging.info(Fore.GREEN + f"Wait for {time_to_notify_dt}" + Style.RESET_ALL)

        # 算出した時間まで待機
        await asyncio.sleep(time_to_notify.total_seconds())

        # 通知タスクを開始
        self.notify.start()

    # ギルド参加時にDBとメンバーを同期
    async def on_guild_join(self, guild: discord.Guild):
        logging.info(
            Fore.GREEN + f"Joined guild {guild.name} ({guild.id})" + Style.RESET_ALL
        )
        self.notify_handler.guild = guild
        await self.notify_handler.notify_member_db_sync()
        logging.info(Fore.GREEN + "Notify task started" + Style.RESET_ALL)
        client.sync_commands()

    # コマンドの実行時にログを出力
    async def on_app_command_completion(
        self,
        interaction: discord.Interaction,
        command: app_commands.Command | app_commands.ContextMenu,
    ):
        command_name = Fore.YELLOW + command.name + Style.RESET_ALL
        user_name = Fore.BLUE + str(interaction.user.name) + Style.RESET_ALL
        user_id = Fore.BLUE + str(interaction.user.id) + Style.RESET_ALL
        guild = Fore.GREEN + str(interaction.guild.name) + Style.RESET_ALL
        channel = Fore.GREEN + str(interaction.channel.name) + Style.RESET_ALL
        timezone = datetime.timezone(datetime.timedelta(hours=9))  # JST
        time = (
            Fore.MAGENTA
            + datetime.datetime.now(timezone).strftime("%Y/%m/%d, %H:%M:%S")
            + Style.RESET_ALL
        )
        logging.info(
            f"{command_name} called by {user_name} ({user_id}) on {guild}, {channel} at {time}"
        )

    ############## my utils ##############

    async def sync_commands(self):
        if self.synced:
            return
        await tree.sync()
        self.synced = True

    @tasks.loop(minutes=10)
    async def set_presence(self):
        timezone = datetime.timezone(datetime.timedelta(hours=9))  # JST
        now = datetime.datetime.now(timezone)
        now_fmt_hm = now.strftime("%H:%M")
        now_fmt_ymd_hms = now.strftime("%Y/%m/%d %H:%M:%S")
        await self.sync_commands()
        await self.change_presence(
            activity=discord.Game(name=f"/help | Synced {now_fmt_hm} (JST)")
        )
        logging.info(
            Fore.GREEN + f"Presence updated at {now_fmt_ymd_hms}" + Style.RESET_ALL
        )

    @tasks.loop(hours=24)
    async def notify(self):
        guild_ids = self.notify_handler.db.get_guilds()
        guilds = [self.get_guild(guild_id) for guild_id in guild_ids]
        dates = [i for i in range(16)]
        for guild in guilds:
            self.notify_handler.guild = guild
            await self.notify_handler.notify_now(dates)


client = Client()
tree = discord.app_commands.CommandTree(client)


############## slash commands ##############


@tree.command(name="ping", description="テスト用の情報を返します")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        ephemeral=True, embed=EmbedHandler(interaction).get_embed_ping()
    )


@tree.command(name="help", description="コマンド一覧を表示します")
async def help(interaction: discord.Interaction):
    # このembedは一時的なものなので、EmbedHandlerを使わない
    commands = {command.name: command.description for command in tree.get_commands()}
    embed = discord.Embed(
        title="コマンド一覧",
        description="\n".join(
            [
                f"**`/{command}`** : {description}"
                for command, description in commands.items()
            ]
        ),
        color=discord.Color.blue(),
    )
    await interaction.response.send_message(ephemeral=True, embed=embed)


@tree.command(name="tag", description="投稿にメンバーをタグ付けします")
async def tag_member_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        ephemeral=True,
        view=TagMemberView1(),
        embed=EmbedHandler(interaction).get_embed_tag(1),
    )


@tree.command(name="untag", description="投稿からメンバーのタグ付けを外します")
async def untag_member_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        ephemeral=True,
        view=UntagMemberView1(),
        embed=EmbedHandler(interaction).get_embed_untag(1),
    )


@tree.command(
    name="tagged_threads", description="メンバーがタグ付けされている投稿を表示します"
)
async def get_tagged_threads_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        ephemeral=True,
        view=GetTaggedthreadsView(),
        embed=EmbedHandler(interaction).get_embed_get_tagged_threads(1),
    )


@tree.command(
    name="tagged_members",
    description="スレッドにタグ付けされているメンバーを表示します",
)
async def get_tagged_members_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        ephemeral=True,
        view=GetTaggedMembersView(),
        embed=EmbedHandler(interaction).get_embed_get_tagged_members(1),
    )


@tree.command(
    name="all_tagged_members",
    description="全てのタグ付けされたメンバーとそのタグ付けされたスレッドを表示します",
)
async def all_tagged_members_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        ephemeral=True, embed=EmbedHandler(interaction).get_embed_all_tagged_members(1)
    )


@tree.command(name="notify_toggle", description="通知のON/OFFを切り替えます")
async def notify_toggle_command(interaction: discord.Interaction):
    notify_db_handler = MemberTaggerNotifyDBHandler()
    current_notify_state = notify_db_handler.get_notify_state(
        interaction.guild.id, interaction.user.id
    )
    await interaction.response.send_message(
        ephemeral=True,
        view=NotifyToggleView(label="切り替える"),
        embed=EmbedHandler(interaction).get_embed_notify_toggle(
            1, current_notify_state
        ),
    )
    del notify_db_handler


@tree.command(
    name="notify_now",
    description="タグ付けされたメンバーに、今すぐ通知を送ります。send_hereをTrueにすると、このチャンネルにまとめて通知を送ります。",
)
async def notify_now_command(interaction: discord.Interaction, send_here: bool = False):
    notify_handler = client.notify_handler
    notify_handler.guild = interaction.guild
    await notify_handler.notify_now_to_channel(
        interaction.channel, interaction
    ) if send_here else await notify_handler.notify_now()


@tree.command(name="invite_url", description="このBotの招待リンクを表示します")
async def invite_command(interaction: discord.Interaction):
    url = discord.utils.oauth_url(
        interaction.application_id, permissions=discord.Permissions(permissions=8)
    )
    await interaction.response.send_message(
        ephemeral=True,
        view=InviteView(url=url),
        embed=EmbedHandler(interaction).get_embed_invite(1),
    )


secret_token = str(os.getenv("DISCORD_BOT_TOKEN_MT"))
client.run(secret_token)
