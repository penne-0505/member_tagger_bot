import datetime

import discord

from components.embeds import EmbedHandler
from db_handler import MemberTaggerDBHandler as DBHandler


handler = DBHandler()

select_types = [
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
]
# FIXME: decide better variable name :(
select_types_for_tagged_mem = [
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
]

class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, current_mode: str):
        super().__init__(
            placeholder='投稿またはチャンネルを選択してください',
            min_values=1,
            max_values=25,
            channel_types=select_types,
        )
        self.current_mode = current_mode
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        channels = interaction.data['values']
        if self.current_mode == 'tag':
            await interaction.response.edit_message(view=TagMemberView2(channels=channels), embed=EmbedHandler(interaction).get_embed_tag(2))
        elif self.current_mode == 'untag':
            await interaction.response.edit_message(view=UntagMemberView2(channels=channels), embed=EmbedHandler(interaction).get_embed_untag(2))
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
                await interaction.response.edit_message(view=None, embed=EmbedHandler(interaction).get_embed_untag(3))
            except Exception as e:
                await interaction.response.edit_message(view=None, embed=EmbedHandler(interaction).get_embed_untag(0))
        else:
            raise ValueError('current_mode must be either "tag" or "untag"')

# TODO: 任意の日数を選択出来るようにする(selectで任意の日数みたいなのを選ばせて、modalで入力させる?)
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
            await interaction.response.edit_message(view=None, embed=EmbedHandler(interaction).get_embed_tag(3))
        except Exception as e:
            await interaction.response.edit_message(view=None, embed=EmbedHandler(interaction).get_embed_tag(0))

# TODO: 複数のメンバーを選択出来るようにする
class GetTaggedthreadsSelect(discord.ui.UserSelect):
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
        threads = handler.get_tagged_threads(selected_member)
        await interaction.response.edit_message(embed=EmbedHandler(interaction).get_embed_get_tagged_threads(2, threads))


class GetTaggedMembersSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder='投稿またはチャンネルを選択してください',
            min_values=1,
            max_values=25,
            channel_types=select_types_for_tagged_mem,
        )
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        target_channels = str(interaction.data['values'][0])
        tagged_members = handler.get_tagged_members(target_channels)
        await interaction.response.edit_message(embed=EmbedHandler(interaction).get_embed_get_tagged_members(2, tagged_members))


class SettingsSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder='変更する設定を選択してください',
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label='【DEV】ChannelSelectで選択可能なチャンネルを変更', value='channel_select_restrict'),
                discord.SelectOption(label='【DEV】GetTaggedMembersSelectで選択可能なチャンネルを変更', value='tagged_mem_select_restrict'),
            ]
        )
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        selected_setting = str(interaction.data['values'][0])
        if selected_setting == 'channel_select_restrict':
            await interaction.response.edit_message(view=ChannelTypeSelect(current_mode='channel_select_restrict'), embed=EmbedHandler(interaction).get_embed_settings(2, 'channel_select_restrict'))
        elif selected_setting == 'tagged_mem_select_restrict':
            await interaction.response.edit_message(view=ChannelTypeSelect(current_mode='tagged_mem_select_restrict'), embed=EmbedHandler(interaction).get_embed_settings(2, 'tagged_mem_select_restrict'))
        else:
            raise ValueError('selected_setting must be either "channel_select_restrict" or "tagged_mem_select_restrict"')

class ChannelTypeSelect(discord.ui.Select):
    def __init__(self, current_mode: str):
        super().__init__(
            placeholder='変更する設定を選択してください',
            min_values=1,
            max_values=25,
            options=[
                discord.SelectOption(label='text', value='text'),
                discord.SelectOption(label='private', value='private'),
                discord.SelectOption(label='voice', value='voice'),
                discord.SelectOption(label='category', value='category'),
                discord.SelectOption(label='news', value='news'),
                discord.SelectOption(label='news_thread', value='news_thread'),
                discord.SelectOption(label='public_thread', value='public_thread'),
                discord.SelectOption(label='private_thread', value='private_thread'),
                discord.SelectOption(label='stage_voice', value='stage_voice'),
                discord.SelectOption(label='forum', value='forum'),
            ]
        )
        self.current_mode = current_mode
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        channel_types = interaction.data['values'] if isinstance(interaction.data['values'], list) else [interaction.data['values']]
        if self.current_mode == 'channel_select_restrict':
            global select_types
            select_types = channel_types
        elif self.current_mode == 'tagged_mem_select_restrict':
            global select_types_for_tagged_mem
            select_types_for_tagged_mem = channel_types
        else:
            raise ValueError('current_mode must be either "channel_select_restrict" or "tagged_mem_select_restrict"')


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='キャンセル', style=discord.ButtonStyle.secondary)
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=discord.abc.MISSING, embed=EmbedHandler(interaction).get_embed_cancel())


async def interaction_check(self, interaction: discord.Interaction):
    if interaction.user == interaction.message.author:
        return True
    else:
        await interaction.response.send_message(silent=True, view=None, embed=EmbedHandler(interaction).get_embed_interaction_error())
        return False

async def on_error(self, interaction: discord.Interaction, error: Exception=None, item=None):
    return interaction.response.send_message(ephemeral=True, view=None, embed=EmbedHandler(interaction).get_embed_error())


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


class GetTaggedthreadsView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(GetTaggedthreadsSelect())
        self.add_item(CancelButton())


class GetTaggedMembersView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(GetTaggedMembersSelect())
        self.add_item(CancelButton())


class SettingsView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item
        self.add_item(CancelButton())