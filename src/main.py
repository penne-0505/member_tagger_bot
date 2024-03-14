import os
import logging

import discord
from colorama import Fore, Style

from db_handler import MemberTaggerDBHandler as DBHandler
from components.embeds import EmbedHandler
from components.views import TagMemberView1, UntagMemberView1, GetTaggedPostsView


intents = discord.Intents.all()
handler = DBHandler()


class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False
    
    async def on_ready(self):
        print(Fore.YELLOW + 'Bot is starting...' + Style.RESET_ALL)
        print(Fore.YELLOW + 'Syncing commands...' + Style.RESET_ALL)
        if not self.synced:
            await self.sync_commands()
        print(Fore.GREEN + 'Commands synced' + Style.RESET_ALL)
        await self.set_presence()
        print(Fore.BLUE + f'Logged in as {self.user.name} ({self.user.id})' + Style.RESET_ALL)
        print(Fore.GREEN + 'Bot is ready' + Style.RESET_ALL)
    
    async def sync_commands(self):
        if self.synced:
            return
        await tree.sync()
        self.synced = True
    
    async def set_presence(self):
        await self.change_presence(activity=discord.CustomActivity(name='Type it: /help', type=discord.ActivityType.listening))


client = Client()
tree = discord.app_commands.CommandTree(client)


@tree.command(name='ping', description='pong')
async def ping(interaction: discord.Interaction):
    to_be_shown_data = {
        'Websocket Latency': round(client.latency * 1000),
        'API Latency': round(client.ws.latency * 1000),
        'Message Author': f'{interaction.user.name}',
        'Message Author ID': f'{interaction.user.id}',
    }
    await interaction.response.send_message(
        embed=discord.Embed(
            title='Pong!',
            description='\n'.join([f'**{key}**: {value}' for key, value in to_be_shown_data.items()]),
            color=discord.Color.green()
        )
    )

@tree.command(name='help', description='コマンド一覧を表示します')
async def help(interaction: discord.Interaction):
    commands = {command.name: command.description for command in await tree.get_commands()}
    commands['ping'] = '通信や処理にかかった時間を返します'
    embed = discord.Embed(
        title='コマンド一覧',
        description='\n'.join([f'`**/{command}**`: {description}' for command, description in commands.items()]),
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="tag", description="投稿にメンバーをタグ付けします")
async def tag_member_command(interaction: discord.Interaction):
    await interaction.response.send_message(ephemeral=True, view=TagMemberView1(), embed=EmbedHandler(step=1, mode='tag').get_embed())

@tree.command(name="untag", description="投稿からメンバーのタグ付けを外します")
async def untag_member_command(interaction: discord.Interaction):
    await interaction.response.send_message(ephemeral=True, view=UntagMemberView1, embed=EmbedHandler(step=1, mode='untag').get_embed())

@tree.command(name="tagged_posts", description="タグ付けされている投稿を表示します")
async def get_tagged_posts_command(interaction: discord.Interaction):
    await interaction.response.send_message(ephemeral=True, view=GetTaggedPostsView, embed=EmbedHandler(step=1, mode='get_tagged_posts').get_embed())


secret_token = str(os.getenv('SECRET_TOKEN'))
client.run(secret_token)