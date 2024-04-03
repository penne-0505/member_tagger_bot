import datetime
import logging

import discord
from  colorama import Fore, Style

from db_handler import MemberTaggerNotifyDBHandler, MemberTaggerDBHandler

logging.basicConfig(level=logging.INFO)

class NotifyHandler:
    def __init__(self, guild: discord.Guild | None = None, interaction: discord.Interaction | None = None):
        if guild or interaction:
            self.guild = guild if guild else interaction.guild
        
        self._interaction = interaction # it wont be used
        self.db = MemberTaggerNotifyDBHandler()
        self.tag_db = MemberTaggerDBHandler()
    
    # シングルトンパターン用
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super().__new__(cls)
        return cls._instance
    
    # 期限が過ぎたスレッドをDBから削除する
    async def _delete_threads_past_deadline(self):
        if not self.guild:
            raise ValueError('guild is not set')
        
        timezone = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(timezone)
        threads = await self.fetch_tagged_threads()
        for member_id, thread_dict in threads.items():
            for thread_id, deadline in thread_dict.items():
                deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d").replace(tzinfo=timezone)
                if deadline < now:
                    self.tag_db.untag_member(member_id, thread_id)
                    logging.info(Fore.GREEN + thread_id + Style.RESET_ALL + 'has been deleted from' + Fore.BLUE + member_id + Style.RESET_ALL)
    
    # 現在参加しているguildとそのメンバーをDBに同期する
    async def notify_member_db_sync(self) -> bool:
        if not self.guild:
            raise ValueError('guild is not set')
        
        if not self.guild.id in self.db.get_guilds():
            self.db.set_guild_id(self.guild.id)
        
        await self._delete_threads_past_deadline()
        
        members = self.guild.members

        for member in members:
            if not self.db.get_notify_state(self.guild.id, member.id):
                self.db.set_notify_state(self.guild.id, member.id, True)
        return True if members == self.db.get_members(self.guild.id) else False
    
    async def fetch_tagged_threads(self) -> dict[str, dict[str, str]]:
        if not self.guild:
            raise ValueError('guild is not set')
        
        # データを取得して、{member_id: {thread_id: deadline}}の形式で返す
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
        
        timezone = datetime.timezone(datetime.timedelta(hours=9)) # JST
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
        if not self.guild:
            raise ValueError('guild is not set')
        
        timezone = datetime.timezone(datetime.timedelta(hours=9)) # JST
        now = datetime.datetime.now(timezone)
        # threadsを日付ごとに整理(15~0日前まで)
        refined = {i: {} for i in range(16)}
        for thread, data in threads.items():
            deadline = data['deadline']
            if not deadline:
                continue
            days = (deadline - now).days + 1
            if days in refined:
                refined[days][thread] = data
        return refined

    async def notify_now(self, target_days: int | list[int] = 0):
        if not self.guild:
            raise ValueError('guild is not set')
        
        await self.notify_member_db_sync()
        threads = await self.fetch_tagged_threads()
        converted = await self.convert_tagged_threads(threads)
        refined = await self.refine_threads(converted)
        if isinstance(target_days, int):
            target_days = [target_days]
        for days in target_days:
            data = refined[days]
            await self._notify_for_one_channel(days, data)
    
    async def notify_now_to_channel(self, channel: discord.TextChannel | discord.Thread, interaction: discord.Interaction | None = None):
        if not self.guild:
            raise ValueError('guild is not set')
        
        await self.notify_member_db_sync()
        threads = await self.fetch_tagged_threads()
        converted = await self.convert_tagged_threads(threads)
        refined = await self.refine_threads(converted)
        
        contents_0 = [await self._get_notify_content(0, data, thread) for thread, data in refined[0].items()]
        contents_1 = [await self._get_notify_content(1, data, thread) for thread, data in refined[1].items()]
        contents_3 = [await self._get_notify_content(3, data, thread) for thread, data in refined[3].items()]
        contents_5 = [await self._get_notify_content(5, data, thread) for thread, data in refined[5].items()]
        contents = contents_0 + contents_1 + contents_3 + contents_5
        

        if contents and interaction:
            embeds = [content['embed'] for content in contents]
            messages = [content['message'] for content in contents]
            formatted_message = str(set([message for message in messages if message])).replace('{', '').replace('}', '').replace("'", '')
            await interaction.response.send_message(embeds=embeds, content=formatted_message)
        
        elif contents and not interaction:
            embeds = [content['embed'] for content in contents]
            messages = [content['message'] for content in contents]
            formatted_message = str(set([message for message in messages if message])).replace('{', '').replace('}', '').replace("'", '')
            await channel.send(embeds=embeds, content=formatted_message)
        
        elif not contents and interaction:
            await interaction.response.send_message(ephemeral=True, delete_after=5.0, embed=discord.Embed(title='通知するものがありませんでした。', color=discord.Color.blue()))
        elif not contents and not interaction:
            await channel.send(embed=discord.Embed(title='通知するものがありませんでした。', color=discord.Color.blue()), silent=True, delete_after=5.0)
        else:
            await interaction.response.send_message(ephemeral=True, delete_after=5.0, embed=discord.Embed(title='通知するものがありませんでした。', description='想定外のケースです。よろしければ管理者に連絡してください。',  color=discord.Color.yellow()))
    
    # 呼び出す側がループを回す
    async def _notify_for_one_channel(self, days: int, data: dict[discord.Thread | discord.TextChannel, dict[str, list[discord.Member] | datetime.datetime]]) -> dict[str, discord.Embed | str]:
        try:
            for thread, data in data.items():
                content = await self._get_notify_content(days, data)
                embed = content['embed']
                message = content['message']
                await thread.send(content=message, embed=embed)
                sent_members = ', '.join([member.name for member in data['members']])
                logging.info(Fore.GREEN + sent_members + Style.RESET_ALL + 'has been notified in' + Fore.BLUE + thread.name + Style.RESET_ALL)
        except Exception as e:
            logging.error(e)
    
    # 呼び出す側がループを回す
    async def _get_notify_content(
        self, 
        days: int,
        data: dict[str, list[discord.Member] | datetime.datetime], 
        thread: discord.Thread | None = None
        ) -> dict[str, discord.Embed | str]:
        # threadを指定した場合は、threadのメンションをつける
        
        members = data['members']
        deadline = data['deadline']
        deadline = deadline.strftime('%Y-%m-%d') if deadline else '未設定'
        member_mentions = [member.mention for member in members]
        if thread:
            embed = discord.Embed(
                title=f'今日が提出期限です！' if days == 0 else f'提出まで{days}日です',
                description=f'提出対象 : {thread.mention}\n提出期限 : {deadline}\n提出者 : {", ".join(member_mentions)}',
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title='今日が提出期限です！' if days == 0 else f'提出まで{days}日です',
                description=f'提出期限 : {deadline}\n提出者 : {", ".join(member_mentions)}',
                color=discord.Color.blue()
            )
        message = ', '.join(member_mentions)
        return {'embed': embed, 'message': message}
