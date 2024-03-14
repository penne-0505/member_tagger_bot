import datetime

import discord

from embeds import EmbedHandler
from db_handler import MemberTaggerDBHandler as DBHandler


handler = DBHandler()

class ViewHandler(discord.ui.View):
    def __init__(self, current_mode: str, step: int, channels: list[str]=None, members: list[str]=None):
        super().__init__()
        self.add_item(CancelButton(self))
        self.current_mode = current_mode
        self.step = step
        self.channels = channels
        self.members = members

    async def tag_member(self, interaction: discord.Interaction):
        if self.step == 1:
            self.add_item(ChannelSelect(current_mode='tag', view_handler=self))
        elif self.step == 2:
            self.add_item(MemberSelect(current_mode='tag', view_handler=self))
        elif self.step == 3:
            self.add_item(DeadlineSelect(view_handler=self))
        await interaction.response.edit_message(view=self)

    async def untag_member(self, interaction: discord.Interaction):
        if self.step == 1:
            self.add_item(ChannelSelect(current_mode='untag', view_handler=self))
        elif self.step == 2:
            self.add_item(MemberSelect(current_mode='untag', view_handler=self))
        await interaction.response.edit_message(view=self)

    async def get_tagged_posts(self, interaction: discord.Interaction):
        if self.step == 1:
            self.add_item(GetTaggedPostsSelect(view_handler=self))
        await interaction.response.edit_message(view=self)


class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, current_mode: str, view_handler: ViewHandler):
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
        self.view_handler = view_handler
        self.interaction_check = interaction_check
        self.on_error = on_error

    async def callback(self, interaction: discord.Interaction):
        channels = interaction.data['values']
        self.view_handler.channels = channels
        if self.current_mode == 'tag':
            await self.view_handler.tag_member(interaction)
        elif self.current_mode == 'untag':
            await self.view_handler.untag_member(interaction)
        else:
            raise ValueError('current_mode must be either "tag" or "untag"')

class MemberSelect(discord.ui.UserSelect):
    def __init__(self, current_mode: str, view_handler: ViewHandler):
        super().__init__(
            placeholder='メンバーを選択してください',
            min_values=1,
            max_values=25,
        )
        self.current_mode = current_mode
        self.view_handler = view_handler
        self.interaction_check = interaction_check
        self.on_error = on_error

    async def callback(self, interaction: discord.Interaction):
        members = interaction.data['values']
        self.view_handler.members = members
        if self.current_mode == 'tag':
            await self.view_handler.tag_member(interaction)
        elif self.current_mode == 'untag':
            await self.view_handler.untag_member(interaction)
        else:
            raise ValueError('current_mode must be either "tag" or "untag"')

class DeadlineSelect(discord.ui.Select):
    def __init__(self, view_handler: ViewHandler):
        super().__init__(
            placeholder='期限を選択してください',
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label='10日後 (Shorts)', emoji='📱', value=10),
                discord.SelectOption(label='15日後 (Default)', emoji='💻', value=15),
            ]
        )
        self.view_handler = view_handler
        self.interaction_check = interaction_check
        self.on_error = on_error

    async def callback(self, interaction: discord.Interaction):
        deadline = (datetime.datetime.now() + datetime.timedelta(days=float(interaction.data['values'][0]))).strftime('%Y-%m-%d')
        try:
            for member in self.view_handler.members:
                for channel in self.view_handler.channels:
                    handler.tag_member(member, channel, deadline)
            await interaction.response.edit_message(view=None, embed=EmbedHandler(step=4, mode='tag').get_embed())
        except Exception as e:
            await interaction.response.edit_message(view=None, embed=EmbedHandler(step=0, mode='tag').get_embed())

class GetTaggedPostsSelect(discord.ui.UserSelect):
    def __init__(self, view_handler: ViewHandler):
        super().__init__(
            placeholder='メンバーを選択してください',
            min_values=1,
            max_values=1,
        )
        self.view_handler = view_handler
        self.interaction_check = interaction_check
        self.on_error = on_error

    async def callback(self, interaction: discord.Interaction):
        selected_member = interaction.data['values'][0]
        posts = handler.get_tagged_posts(selected_member)
        await interaction.response.edit_message(embeds=[EmbedHandler(step=2, mode='get_tagged_posts', posts=posts, interaction=interaction).get_embed()])

class CancelButton(discord.ui.Button):
    def __init__(self, view_handler: ViewHandler):
        super().__init__(label='キャンセル', style=discord.ButtonStyle.secondary)
        self.view_handler = view_handler
        self.interaction_check = interaction_check
        self.on_error = on_error

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None, embed=EmbedHandler(step=0, mode=self.view_handler.current_mode).get_embed_cancelled())


async def interaction_check(self, interaction: discord.Interaction):
    if interaction.user == interaction.message.author:
        return True
    else:
        await interaction.response.send_message(silent=True, view=None, embed=EmbedHandler(step=0, mode=self.view_handler.current_mode).get_embed_interaction_error())
        return False

async def on_error(self, interaction: discord.Interaction, error: Exception=None, item=None):
    return interaction.response.send_message(ephemeral=True, view=None, embed=EmbedHandler(step=0, mode=self.view_handler.current_mode).get_embed_error())

if __name__ == '__main__':
    pass