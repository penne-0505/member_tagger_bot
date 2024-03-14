import datetime

import discord

from db_handler import MemberTaggerDBHandler


class EmbedHandler:
    def __init__(self, step: int, mode: str, posts: dict[dict[str, str]] = None, interaction: discord.Interaction = None):
        self.step = step
        self.mode = mode
        self.posts = posts
        self.interaction = interaction

    def get_embed(self):
        if self.mode == 'tag':
            if self.step == 1:
                embed = discord.Embed(
                    title='1. 投稿を選択',
                    description='タグ付けを行うチャンネルを選択してください',
                    color=discord.Color.blue()
                )
            elif self.step == 2:
                embed = discord.Embed(
                    title='2. メンバーのタグ付け',
                    description='チャンネルにタグ付けを行うメンバーを選択してください',
                    color=discord.Color.blue()
                )
            elif self.step == 3:
                embed = discord.Embed(
                    title='3. 期限を選択',
                    description='提出までの期限を選択してください',
                    color=discord.Color.blue()
                )
            elif self.step == 4:
                embed = self.get_embed_success('タグ付け')
            else:
                embed = self.get_embed_error()

        elif self.mode == 'untag':
            if self.step == 1:
                embed = discord.Embed(
                    title='1. チャンネルを選択',
                    description='タグ付けを解除するチャンネルを選択してください',
                    color=discord.Color.blue()
                )
            elif self.step == 2:
                embed = discord.Embed(
                    title='2. メンバーを選択',
                    description='チャンネルからタグ付けを解除するメンバーを選択してください',
                    color=discord.Color.blue()
                )
            elif self.step == 3:
                embed = self.get_embed_success('タグ付けの解除')
            else:
                embed = self.get_embed_error()

        elif self.mode == 'get_tagged_posts':
            if self.step == 1:
                embed = discord.Embed(
                    title='1. メンバーを選択',
                    description='タグ付けされた投稿を表示するメンバーを選択してください',
                    color=discord.Color.blue()
                )
            elif self.step == 2:
                self.posts = self.posts.pop('member_id', None)
                target_channels_id = [int(post) for post in self.posts.keys()]
                target_channels = [self.interaction.guild.get_thread(channel_id) for channel_id in target_channels_id]
                channels_deadline = [deadline for deadline in self.posts.values()]
                self.channels = [f'・{channel.mention} \n    提出期限 : {deadline}\n    残り : {str((datetime.datetime.strptime(deadline, "%Y-%m-%d") - datetime.datetime.now()).days)} 日' for channel, deadline in zip(target_channels, channels_deadline)]
                embed = discord.Embed(
                    title='**取得結果：**\n' + '\n\n'.join([f'{post}' for post in self.channels]),
                    color=discord.Color.green(),
                )
            else:
                embed = self.get_embed_error()

        else:
            embed = self.get_embed_error()

        return embed

    def get_embed_error(self):
        return discord.Embed(
            title='エラーが発生しました (exception error)',
            color=discord.Color.red()
        )

    def get_embed_cancelled(self):
        return discord.Embed(
            title='操作がキャンセルされました (cancelled)',
            color=discord.Color.blue()
        )

    def get_embed_success(self, task: str = None):
        task = task if task else '処理'
        return discord.Embed(
            title=f'{task}が完了しました',
            color=discord.Color.green()
        )

    def get_embed_interaction_error(self):
        return discord.Embed(
            title='エラーが発生しました (interaction author error)',
            description='UIの操作はコマンド実行者のみが行えます',
            color=discord.Color.red()
        )