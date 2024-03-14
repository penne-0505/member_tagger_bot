import datetime

import discord

# TODO: implement better variable type validation

class EmbedHandler:
    '''
    EmbedHandler class
    
    ### Overview
    EmbedHandler class is a class that handles the creation of embeds for the bot.
    
    ### Example
    
    #### Creating a basic embed
    ```python
    embed = EmbedHandler(mode='tag', step=1).get_embed()
    ```
    
    #### Creating an error embed
    ```python
    embed = EmbedHandler(mode='{something}', step=0).get_embed()
    embed = EmbedHandler(mode='error').get_embed()
    embed = EmbedHandler().get_embed_error()
    # All are the same
    ```
    - get_embed_error, get_embed_cancel, get_embed_success, and get_embed_interaction_error are also available
    
    ### Arguments
    - `mode` : str : The mode of the embed.
    - `step` : int : The step of the embed.
    - `posts` : dict[dict[str, str]] : The posts to be displayed in the embed.
    - `interaction` : discord.Interaction : The interaction object.
    '''
    def __init__(self, mode: str = None, step: int = None, posts: dict[dict[str, str]] = None, interaction: discord.Interaction = None):
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
                # i think there's better way to handle this(but even if you display the error text as it is to the user...)
                if not self.step:
                    embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
                elif not self.interaction:
                    embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
                else:
                    embed = self.get_embed_error(title='エラーが発生しました (unknown error)')

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
                if not self.step:
                    embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
                elif not self.interaction:
                    embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
                else:
                    embed = self.get_embed_error(title='エラーが発生しました (unknown error)')

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
                
                if not self.step:
                    embed = self.get_embed_error(title='エラーが発生しました (step is None or invalid)')
                elif not self.posts:
                    embed = self.get_embed_error(title='エラーが発生しました (posts is None or invalid)')
                elif not self.interaction:
                    embed = self.get_embed_error(title='エラーが発生しました (interaction is None or invalid)')
                else:
                    embed = self.get_embed_error(title='エラーが発生しました (unknown error)')
            
        elif self.mode == 'error':
            embed = self.get_embed_error()
        
        elif self.mode == 'cancelled':
            embed = self.get_embed_cancel()
        
        elif self.mode == 'success':
            embed = self.get_embed_success()
        
        elif self.mode == 'interaction_error':
            embed = self.get_embed_interaction_error()
        
        else:
            embed = self.get_embed_error(title='エラーが発生しました (mode is None or invalid)')

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