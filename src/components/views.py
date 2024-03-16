import datetime
import asyncio

import discord

from components.embeds import EmbedHandler
from db_handler import MemberTaggerDBHandler as DBHandler


handler = DBHandler()

class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, current_mode: str):
        super().__init__(
            placeholder='投稿またはチャンネルを選択してください',
            min_values=1,
            max_values=25,
            channel_types=[
                discord.ChannelType.public_thread,
                discord.ChannelType.private_thread,
            ],
        )
        self.current_mode = current_mode
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        channels = interaction.data['values']
        if self.current_mode == 'tag':
            await interaction.response.edit_message(view=TagMemberView2(channels=channels), embed=EmbedHandler(step=2, mode='tag').get_embed())
        elif self.current_mode == 'untag':
            await interaction.response.edit_message(view=UntagMemberView2(channels=channels), embed=EmbedHandler(step=2, mode='untag').get_embed())
        else:
            raise ValueError('current_mode must be either "tag" or "untag"')

class MemberSelect(discord.ui.UserSelect):
    def __init__(self, current_mode: str, channels: list[str]):
        super().__init__(
            placeholder='メンバーを選択してください',
            min_values=1,
            max_values=25,
        )
        self.current_mode = current_mode
        self.channels = channels
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        global members
        members = interaction.data['values']
        if self.current_mode == 'tag':
            await interaction.response.edit_message(view=TagMemberView3(channels=self.channels, members=members), embed=EmbedHandler(step=3, mode='tag').get_embed())
        elif self.current_mode == 'untag':
            try:
                for member in members:
                    for channel in self.channels:
                        handler.untag_member(member, channel)
                await interaction.response.edit_message(view=None, embed=EmbedHandler(step=3, mode='untag').get_embed())
            except Exception as e:
                await interaction.response.edit_message(view=None, embed=EmbedHandler(step=0, mode='untag').get_embed())
        else:
            raise ValueError('current_mode must be either "tag" or "untag"')

class DeadlineSelect(discord.ui.Select):
    def __init__(self, channels: list[str], members: list[str]):
        super().__init__(
            placeholder='期限を選択してください',
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label='10日後 (Shorts)', emoji='📱', value=10),
                discord.SelectOption(label='15日後 (Default)', emoji='💻', value=15),
            ]
        )
        self.channels = channels
        self.members = members
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        deadline = (datetime.datetime.now() + datetime.timedelta(days=float(interaction.data['values'][0]))).strftime('%Y-%m-%d')
        try:
            for member in self.members:
                for channel in self.channels:
                    handler.tag_member(member, channel, deadline)
            await interaction.response.edit_message(view=None, embed=EmbedHandler(step=4, mode='tag').get_embed())
        except Exception as e:
            await interaction.response.edit_message(view=None, embed=EmbedHandler(step=0, mode='tag').get_embed())

# TODO: 複数のメンバーを選択出来るようにする
class GetTaggedPostsSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(
            placeholder='メンバーを選択してください',
            min_values=1,
            max_values=1,
            )
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        selected_member = str(interaction.data['values'][0])
        posts = handler.get_tagged_posts(selected_member)
        await interaction.response.edit_message(embed=EmbedHandler(mode='get_tagged_posts', step=2, posts=posts, interaction=interaction).get_embed())


class GetTaggedMembersSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder='投稿またはチャンネルを選択してください',
            min_values=1,
            max_values=25,
            channel_types=[
                discord.ChannelType.public_thread,
                discord.ChannelType.private_thread,
            ],
        )
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        channels = str(interaction.data['values'][0])
        result = handler.get_tagged_members(channels)
        await interaction.response.edit_message(embed=EmbedHandler(mode='get_tagged_members', step=2, members=result, interaction=interaction).get_embed())


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='キャンセル', style=discord.ButtonStyle.secondary)
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None, embed=EmbedHandler().get_embed_cancel())


async def interaction_check(self, interaction: discord.Interaction):
    if interaction.user == interaction.message.author:
        return True
    else:
        await interaction.response.send_message(silent=True, view=None, embed=EmbedHandler().get_embed_interaction_error())
        return False

async def on_error(self, interaction: discord.Interaction, error: Exception=None, item=None):
    return interaction.response.send_message(ephemeral=True, view=None, embed=EmbedHandler().get_embed_error())


class TagMemberView1(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ChannelSelect(current_mode='tag'))
        self.add_item(CancelButton())

class TagMemberView2(discord.ui.View):
    def __init__(self, channels: list[str]):
        super().__init__()
        self.add_item(MemberSelect(current_mode='tag', channels=channels))
        self.add_item(CancelButton())

class TagMemberView3(discord.ui.View):
    def __init__(self, channels: list[str], members: list[str]):
        super().__init__()
        self.add_item(DeadlineSelect(channels=channels, members=members))
        self.add_item(CancelButton())


class UntagMemberView1(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ChannelSelect(current_mode='untag'))
        self.add_item(CancelButton())

class UntagMemberView2(discord.ui.View):
    def __init__(self, channels: list[str]):
        super().__init__()
        self.add_item(MemberSelect(current_mode='untag', channels=channels))
        self.add_item(CancelButton())


class GetTaggedPostsView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(GetTaggedPostsSelect())
        self.add_item(CancelButton())


class GetTaggedMembersView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(GetTaggedMembersSelect())
        self.add_item(CancelButton())