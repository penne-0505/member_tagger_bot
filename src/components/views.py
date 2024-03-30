import datetime

import discord

from components.embeds import EmbedHandler
from db_handler import MemberTaggerDBHandler, MemberTaggerNotifyDBHandler

# ? クラス側で__new__でシングルトンにしたほうがいい？
# TODO: インスタンスの管理、リソース管理をもっと考える
db_handler = MemberTaggerDBHandler()
notify_handler = MemberTaggerNotifyDBHandler()

# FIXME: もっといい変数名と仕組み
select_types = [
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
]
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
            members = db_handler.get_tagged_members(str(channels[0]))
            await interaction.response.edit_message(view=UntagMemberView2(channels=channels), embed=EmbedHandler(interaction).get_embed_untag(2, members))
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
            await interaction.response.edit_message(view=TagMemberView3(channels=self.channels, members=members), embed=EmbedHandler(interaction).get_embed_tag(3))
        elif self.current_mode == 'untag':
            try:
                for member in members:
                    for channel in self.channels:
                        db_handler.untag_member(member, channel)
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

        deadline = (
            datetime.datetime.now() + datetime.timedelta(days=float(interaction.data['values'][0]))
            ).strftime('%Y-%m-%d')
        
        try:
            for member in self.members:
                for channel in self.channels:
                    db_handler.tag_member(member, channel, deadline)
            await interaction.response.edit_message(view=None, embed=EmbedHandler(interaction).get_embed_tag(4))
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
        threads = db_handler.get_tagged_threads(selected_member)
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
        tagged_members = db_handler.get_tagged_members(target_channels)
        await interaction.response.edit_message(embed=EmbedHandler(interaction).get_embed_get_tagged_members(2, tagged_members))


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='キャンセル', style=discord.ButtonStyle.secondary)
        self.interaction_check = interaction_check
        self.on_error = on_error
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=discord.abc.MISSING, embed=EmbedHandler(interaction).get_embed_cancel())

class ConfirmButton(discord.ui.Button):
    def __init__(self, current_mode: str):
        super().__init__(label='OK', style=discord.ButtonStyle.primary, row=0)
        self.interaction_check = interaction_check
        self.on_error = on_error
        self.current_mode = str(current_mode)
    
    async def callback(self, interaction: discord.Interaction):
        # TODO: 処理系は別の関数に移す
        if self.current_mode == 'notify_toggle':
            modified_state = notify_handler.toggle_notify_state(interaction.guild.id, interaction.user.id)
            await interaction.response.edit_message(view=None, embed=EmbedHandler(interaction).get_embed_notify_toggle(step=2, current_state=modified_state))
        else:
            pass


async def interaction_check(self, interaction: discord.Interaction):
    if interaction.user == interaction.message.author:
        return True
    else:
        await interaction.response.send_message(silent=True, view=None, embed=EmbedHandler(interaction).get_embed_interaction_error())
        return False

async def on_error(self, interaction: discord.Interaction, error: Exception=None, item=None):
    return interaction.response.send_message(ephemeral=True, view=None, embed=EmbedHandler(interaction).get_embed_error())


# TODO: これらのViewをもっと綺麗に書くか、EmbedHandlerみたいに単一クラスにまとめる
class TagMemberView1(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(ChannelSelect(current_mode='tag'))
        self.add_item(CancelButton())

class TagMemberView2(discord.ui.View):
    def __init__(self, channels: list[str]):
        super().__init__(timeout=60)
        self.add_item(MemberSelect(current_mode='tag', channels=channels))
        self.add_item(CancelButton())

class TagMemberView3(discord.ui.View):
    def __init__(self, channels: list[str], members: list[str]):
        super().__init__(timeout=60)
        self.add_item(DeadlineSelect(channels=channels, members=members))
        self.add_item(CancelButton())


class UntagMemberView1(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(ChannelSelect(current_mode='untag'))
        self.add_item(CancelButton())

class UntagMemberView2(discord.ui.View):
    def __init__(self, channels: list[str]):
        super().__init__(timeout=60)
        self.add_item(MemberSelect(current_mode='untag', channels=channels))
        self.add_item(CancelButton())


class GetTaggedthreadsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(GetTaggedthreadsSelect())
        self.add_item(CancelButton())


class GetTaggedMembersView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(GetTaggedMembersSelect())
        self.add_item(CancelButton())


class NotifyToggleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(ConfirmButton(current_mode='notify_toggle'))
        self.add_item(CancelButton())