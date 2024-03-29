import datetime
from typing import Any

import discord

# TODO: implement better variable type validation

class EmbedHandler:
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
    
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
    
    def get_embed_untag(self, step: int, interaction: discord.Interaction):
        if step == 1:
            embed = discord.Embed(
                title='1. 投稿を選択',
                description='タグ付けを解除する投稿を選択してください',
                color=discord.Color.blue()
            )
        elif step == 2:
            embed = discord.Embed(
                title='2. メンバーを選択',
                description='投稿からタグ付けを解除するメンバーを選択してください',
                color=discord.Color.blue()
            )
        elif step == 3:
            embed = self.get_embed_success('タグ付けの解除')
        else:
            if not step:
                embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
            elif not interaction:
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
                
                print(target_channels, channel_deadlines)
                timezone = datetime.timezone(datetime.timedelta(hours=9))
                self.channels = [f'・{channel.mention} \n    提出期限 : {deadline}\n    残り : {str((datetime.datetime.strptime(deadline, "%Y-%m-%d").replace(tzinfo=timezone) - datetime.datetime.now(timezone)).days)} 日' for channel, deadline in zip(target_channels, channel_deadlines)]
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
    
    def get_embed_notify_toggle(self, step: int, current_state: bool | None = None):
        if step == 1:
            embed = discord.Embed(
                title=f'通議をON/OFFに切り替えます (現在の状態 : {"ON" if current_state else "OFF"})',
                color=discord.Color.blue()
            )
        elif step == 2:
            embed = self.get_embed_success(f'通知のON/OFFを切り替えました (現在の状態 : {"ON" if current_state else "OFF"})')
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
                title='招待リンク',
                description=f'`{url}`',
                color=discord.Color.blue()
            )
        else:
            if not step:
                embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
            elif not self.interaction:
                embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
            else:
                embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
        return embed

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