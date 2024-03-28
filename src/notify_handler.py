import datetime

import discord
from discord.ext import tasks

from db_handler import MemberTaggerNotifyDBHandler, MemberTaggerDBHandler

'''
1. 規定時刻まで待つ(12時か0時)(これはtask.loopで時刻を指定して実行する)
2. ギルドごとに
    1. タグ付けされた投稿とメンバーの辞書を取得
    2. {member: {thread_id: deadline}, ...}となっている辞書を{thread_id: {'members': [member_id, ...], 'deadline': deadline}に変換
    3. notifyがTrueのメンバーに対して、deadlineが近づいている投稿を取得
    4. 通知をthreadごとに送信
3. 変数を初期化して、1に戻る
'''

class NotifyHandler:
    def __init__(self, guild: discord.Guild | None = None, interaction: discord.Interaction | None = None):
        if guild or interaction:
            self.guild = guild if guild else interaction.guild
        else:
            print('guild or interaction is not given (ignored)')
        self._interaction = interaction # it wont be used
        self.db = MemberTaggerNotifyDBHandler()
        self.tag_db = MemberTaggerDBHandler()
    
    async def notify_member_db_sync(self) -> bool:
        if not self.guild:
            raise ValueError('guild is not set')
        
        if not self.guild.id in self.db.get_guilds():
            self.db.set_guild_id(self.guild.id)
        
        members = self.guild.members

        for member in members:
            if not self.db.get_notify_state(self.guild.id, member.id):
                self.db.set_notify_state(self.guild.id, member.id, True)
        return True if members == self.db.get_members(self.guild.id) else False
    
    async def fetch_tagged_threads(self) -> dict[str, dict[str, str]]:
        if not self.guild:
            raise ValueError('guild is not set')
        
        member_ids = self.db.get_members(self.guild.id)
        threads = {}
        for member_id in member_ids:
            threads[member_id] = self.tag_db.get_tagged_threads(member_id)
        return threads
    
    async def convert_tagged_threads(
        self,
        threads: dict[str, dict[str, str]]
        ) -> dict[discord.Thread | discord.TextChannel, dict[str, list[discord.Member] | datetime.datetime]]:
        '''
        return {thread: {'members': [member, ...], 'deadline': deadline}}
        '''
        if not self.guild:
            raise ValueError('guild is not set')
        
        timezone = datetime.timezone(datetime.timedelta(hours=9))
        converted = {}
        for member_id, thread_dict in threads.items():
            for thread_id, deadline in thread_dict.items():
                thread = self.guild.get_channel_or_thread(int(thread_id))
                deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d").replace(tzinfo=timezone) if deadline else None
                if not thread:
                    continue
                if thread not in converted:
                    converted[thread] = {'members': [], 'deadline': deadline}
                converted[thread]['members'].append(self.guild.get_member(int(member_id)))
        return converted
    
    # TODO: 型エイリアスを使って、型を簡潔に表現するようにする
    async def refine_threads(
        self,
        threads: dict[discord.Thread | discord.TextChannel, dict[str, list[discord.Member] | datetime.datetime]]
        ) -> dict[int, dict[discord.Thread | discord.TextChannel, dict[str, list[discord.Member] | datetime.datetime]]]:
        '''return threads that deadline is within 5, 3, 1, 0 day(s)\nreturn {days: {thread: {'members': [member, ...], 'deadline': deadline}}}'''
        if not self.guild:
            raise ValueError('guild is not set')
        
        timezone = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(timezone)
        refined = {5: {}, 3: {}, 1: {}, 0: {}}
        for thread, data in threads.items():
            deadline = data['deadline']
            if not deadline:
                continue
            days = (deadline - now).days
            if days in refined:
                refined[days][thread] = data
        return refined

    async def notify_now(self, target_days: int | list[int] = 0):
        '''target_days expects 0, 1, 3, 5\nif target_days is not given, notify all threads'''
        if not self.guild:
            raise ValueError('guild is not set')
        
        await self.notify_member_db_sync()
        threads = await self.fetch_tagged_threads()
        converted = await self.convert_tagged_threads(threads)
        refined = await self.refine_threads(converted)
        if isinstance(target_days, int):
            target_days = [target_days]
        for days in target_days:
            for data in refined[days].values():
                await self._notify_for_one_channel(days, data)
    
    async def notify_now_to_channel(self, channel: discord.TextChannel | discord.Thread):
        if not self.guild:
            raise ValueError('guild is not set')
        
        await self.notify_member_db_sync()
        threads = await self.fetch_tagged_threads()
        converted = await self.convert_tagged_threads(threads)
        refined = await self.refine_threads(converted)
        content_0 = [await self._get_notify_content(0, data) for data in refined[0].values()]
        content_1 = [await self._get_notify_content(1, data) for data in refined[1].values()]
        content_3 = [await self._get_notify_content(3, data) for data in refined[3].values()]
        content_5 = [await self._get_notify_content(5, data) for data in refined[5].values()]
        contents = content_0 + content_1 + content_3 + content_5
        if contents:
            for content in contents:
                await channel.send(content=content['message'], embed=content['embed'])
        else:
            await channel.send(embed=discord.Embed(title='通知するものがありませんでした', color=discord.Color.blue()), silent=True, delete_after=5.0)
        
    # 呼び出す側がループを回す
    async def _notify_for_one_channel(self, days: int, data: dict[discord.Thread | discord.TextChannel, dict[str, list[discord.Member] | datetime.datetime]]) -> dict[str, discord.Embed | str]:
        for thread, data in data.items():
            content = await self._get_notify_content(days, data)
            embed = content['embed']
            message = content['message']
            await thread.send(content=message, embed=embed)
        return {'embed': embed, 'message': message}
    
    # 呼び出す側がループを回す
    async def _get_notify_content(self, days: int, data: dict[str, list[discord.Member] | datetime.datetime]) -> dict[str, discord.Embed | str]:
        members = data['members']
        deadline = data['deadline']
        deadline = deadline.strftime('%Y-%m-%d') if deadline else '未設定'
        member_mentions = [member.mention for member in members]
        embed = discord.Embed(
            title='今日が提出期限です！' if days == 0 else f'提出期限が{days}日後です',
            description=f'提出期限 : {deadline}\n提出者 : {", ".join(member_mentions)}',
            color=discord.Color.green()
        )
        message = ', '.join(member_mentions)
        return {'embed': embed, 'message': message}
