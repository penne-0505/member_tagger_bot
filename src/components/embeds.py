import datetime
from typing import Any

import discord

from db_handler import MemberTaggerDBHandler


class Singleton(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class EmbedHandler(metaclass=Singleton):
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.db_handler = MemberTaggerDBHandler()
    
    
    def get_embed_ping(self):
        data = {
            'Latency': f'`{round(self.interaction.client.latency * 1000)}ms`',
            'Now': f'{datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y/%m/%d %H:%M:%S  timezone: %Z")}',
            'Message Author': f'{self.interaction.user.mention} (`{self.interaction.user.id}`)',
            'Guild': f'{self.interaction.guild.name} (`{self.interaction.guild.id}`)' if self.interaction.guild else 'DM',
            'Channel': f'{self.interaction.channel.mention} (`{self.interaction.channel.id}`)' if self.interaction.guild else 'DM',
        }
        return discord.Embed(
            title='Pong!',
            description='\n'.join([f'**{key}**: {value}' for key, value in data.items()]),
            color=discord.Color.green()
        )
    
    def get_embed_tag(self, step: int):
        if step == 1:
                embed = discord.Embed(
                    title='1. 投稿を選択',
                    description='タグ付けを行う投稿を選択してください',
                    color=discord.Color.blue()
                )
        elif step == 2:
            embed = discord.Embed(
                title='2. メンバーのタグ付け',
                description='投稿にタグ付けを行うメンバーを選択してください',
                color=discord.Color.blue()
            )
        elif step == 3:
            embed = discord.Embed(
                title='3. 期限を選択',
                description='提出までの期限を選択してください',
                color=discord.Color.blue()
            )
        elif step == 4:
            embed = self.get_embed_success('タグ付け')
        else:
            # i think there's better way to handle this(but even if you display the error text as it is to the user...)
            if not step:
                embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
            elif not self.interaction:
                embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
            else:
                embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
        return embed
    
    def get_embed_untag(self, step: int, thread_info: dict[str, str] | None = None):
        if step == 1:
            embed = discord.Embed(
                title='1. 投稿を選択',
                description='タグ付けを解除する投稿を選択してください',
                color=discord.Color.blue()
            )
        elif step == 2:
            tagged_members = []
            for member_id in thread_info['ids']:
                tagged_members.append(self.interaction.guild.get_member(int(member_id)))
            
            if not tagged_members:
                embed = discord.Embed(title='取得結果：', description='タグ付けされたメンバーはいませんでした', color=discord.Color.green())
                return embed
            
            embed = discord.Embed(
                title='2. メンバーを選択',
                description=f'投稿からタグ付けを解除するメンバーを選択してください\n\n現在タグ付けされているメンバー:\n' + '\n'.join([f'{member.mention}' for member in tagged_members]),
                color=discord.Color.blue()
            )
        elif step == 3:
            embed = self.get_embed_success('タグ付けの解除')
        else:
            if not step:
                embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
            elif not self.interaction:
                embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
            else:
                embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
        return embed

    def get_embed_get_tagged_threads(self, step: int, threads: dict[str, str] | None = None):
        if step == 1:
            embed = discord.Embed(
                title='1. メンバーを選択',
                description='タグ付けされた投稿を表示するメンバーを選択してください',
                color=discord.Color.blue()
            )
        elif step == 2:
            if not threads:
                embed = discord.Embed(title='取得結果：', description='タグ付けされた投稿はありません', color=discord.Color.green())
                return embed
            else:
                target_channels = []
                channel_deadlines = []
                for thread, deadline in threads.items():
                    if self.interaction.guild.get_channel_or_thread(int(thread)):
                        target_channels.append(self.interaction.guild.get_channel_or_thread(int(thread)))
                        channel_deadlines.append(deadline)
                
                timezone = datetime.timezone(datetime.timedelta(hours=9))
                self.channels = [f'・{channel.mention} \n    提出期限 : {deadline}\n    残り : {str((datetime.datetime.strptime(deadline, "%Y-%m-%d").replace(tzinfo=timezone) - datetime.datetime.now(timezone)).days + 1)} 日' for channel, deadline in zip(target_channels, channel_deadlines)]
                embed = discord.Embed(
                    title='**取得結果：**\n' + '\n\n'.join([f'{thread}' for thread in self.channels]),
                    color=discord.Color.green(),
                )
        else:
            if not step:
                embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
            elif not threads:
                embed = self.get_embed_error(title='エラーが発生しました (threads is None or invalid)')
            elif not self.interaction:
                embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
            else:
                embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
        return embed

    def get_embed_get_tagged_members(self, step: int, members: dict[str, Any] | None = None):
        if step == 1:
            embed = discord.Embed(
                title='1. 投稿を選択',
                description='タグ付けされたメンバーを表示する投稿を選択してください',
                color=discord.Color.blue()
            )
        elif step == 2:
            if not members:
                embed = discord.Embed(title='取得結果：', description='タグ付けされたメンバーはいませんでした', color=discord.Color.green())
                return embed
            else:
                target_member_ids = [member for member in members['ids']]
                raw_deadline = members['deadline']
                members = [f'・ {self.interaction.guild.get_member(int(member_id)).mention}' for member_id in target_member_ids]
                num_of_days = str((datetime.datetime.strptime(raw_deadline, "%Y-%m-%d") - datetime.datetime.now()).days + 1) if raw_deadline else None
                if not members and num_of_days:
                    embed = discord.Embed(
                        title='タグ付けされたメンバーはいませんでした',
                        description='ですが、今回のケースは想定外です。よろしければ管理者か開発者に連絡してください。',
                        color=discord.Color.yellow()
                    )
                elif members and not num_of_days:
                    embed = discord.Embed(
                        title=f'**取得結果：**\n' + '\n'.join([f'{member}' for member in members]),
                        description='提出期限が見つかりませんでした。今回のケースは想定外です。よろしければ管理者か開発者に連絡してください。',
                        color=discord.Color.green()
                    )
                elif not members and not num_of_days:
                    embed = discord.Embed(title='取得結果：', description='タグ付けされたメンバーはいませんでした', color=discord.Color.green())
                else:
                    embed = discord.Embed(
                        title='**取得結果：**',
                        description='\n'.join([f'{member}' for member in members]) + f'\n\n提出期限 : {raw_deadline}\n残り : {num_of_days} 日',
                        color=discord.Color.green()
                    )
                return embed
        else:
            if not step:
                embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
            elif not members:
                embed = self.get_embed_error(title='エラーが発生しました (members is None or invalid)')
            elif not self.interaction:
                embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
            else:
                embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
        return embed
    
    
    def format_member_threads(self, refined_threads: dict[str, dict[str, str]]):
        def format_thread(thread_id, deadline):
            channel = self.interaction.guild.get_channel_or_thread(int(thread_id))
            if channel:
                return f'    **{channel.mention}** : {deadline}'
            return None

        def format_member(member_id, threads: dict[str, str]):
            member = self.interaction.guild.get_member(int(member_id))
            if member:
                threads_str = '\n - '.join(thread for thread in (format_thread(thread_id, deadline) for thread_id, deadline in threads.items()) if thread)
                if threads_str:
                    return f'- **{member.mention} :** \n    - {threads_str}'
            return None

        return '\n\n'.join(member for member in (format_member(member_id, threads) for member_id, threads in refined_threads.items()) if member)
    
    def get_embed_all_tagged_members(self, step: int | None = None):
        
        if step == 1:
            all_threads = self.db_handler.get_all_tagged_threads()
            refined_threads = {member_id: threads for member_id, threads in all_threads.items() if threads}
            description = self.format_member_threads(refined_threads)
            if description:
                embed = discord.Embed(
                    title='取得結果：',
                    description=description,
                    color=discord.Color.green()
                )
            elif not description:
                embed = discord.Embed(
                    title='取得結果：',
                    description='タグ付けされたメンバーはいませんでした',
                    color=discord.Color.green()
                )
            else:
                embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
        else:
            if not step:
                embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
            elif not self.interaction:
                embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
            else:
                embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
        return embed
    
    def get_embed_notify_toggle(self, step: int, current_state: bool | None = None):
        if step == 1:
            title = f'通知のON/OFFを切り替えますか？ (現在の設定: **{"ON" if current_state else "OFF"}**)'
            embed = discord.Embed(
                title=title,
                color=discord.Color.blue()
            )
        elif step == 2:
            title = f'通知のON/OFFを切り替えました (現在の設定: **{"ON" if current_state else "OFF"}**)'
            embed = discord.Embed(
                title=title,
                color=discord.Color.green()
            )
        else:
            if not step:
                embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
            elif not self.interaction:
                embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
            else:
                embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
        return embed
    
    def get_embed_invite(self, step: int | None):
        if step == 1:
            url = discord.utils.oauth_url(self.interaction.application_id, permissions=discord.Permissions(permissions=8))
            embed = discord.Embed(
                title='招待リンク (スマホなら長押しでコピー)',
                description=url,
                color=discord.Color.blue()
            )
        elif step == 2:
            embed = discord.Embed(
                title='リンクを表示しました',
                color=discord.Color.green()
            )
        else:
            if not step:
                embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
            elif not self.interaction:
                embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
            else:
                embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
        return embed

    ############ common embeds ############
    
    def get_embed_error(self, title: str = None, description: str = None):
        return discord.Embed(
            title='エラーが発生しました (exception error)' if not title else title,
            description='もう一度やり直してください。何度もエラーが出る場合は管理者に連絡してください' if not description else description,
            color=discord.Color.red()
        )

    def get_embed_cancel(self, title: str = None, description: str = None):
        return discord.Embed(
            title='操作がキャンセルされました (cancelled)' if not title else title,
            description=None if not description else description,
            color=discord.Color.blue()
        )

    def get_embed_success(self, task: str = None, title: str = None, description: str = None):
        task = task if task else '処理'
        return discord.Embed(
            title=f'{task}が完了しました' if not title else title,
            description=None if not description else description,
            color=discord.Color.green()
        )

    def get_embed_interaction_error(self, title: str = None, description: str = None):
        return discord.Embed(
            title='エラーが発生しました (interaction author error)' if not title else title,
            description='UIの操作はコマンド実行者のみが行えます' if not description else description,
            color=discord.Color.red()
        )
    
    def get_embed_finished(self, title: str = None, description: str = None):
        return discord.Embed(
            title='操作が完了しました' if not title else title,
            description=None if not description else description,
            color=discord.Color.green()
        )
