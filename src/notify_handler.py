import datetime
import logging
from discord.ext import tasks

import discord

from db_handler import MemberTaggerNotifyDBHandler, MemberTaggerDBHandler

class NotifyHandler:
    def __init__(self, interaction: discord.Interaction | None = None, guild: discord.Guild | None = None):
        self.interaction = interaction
        self.threads_db_handler = MemberTaggerDBHandler()
        self.notify_db_handler = MemberTaggerNotifyDBHandler()
        self.guild = guild
    
    async def _notify(self, target_members: dict[str, dict[discord.Thread, datetime.datetime]], until: int = None):
        
        for member_id, threads in target_members.items():
            member = self.interaction.guild.get_member(int(member_id)) if self.interaction else self.guild.get_member(int(member_id))
            embed = discord.Embed(
                title='',
                description='',
                color=discord.Color.yellow()
            )
            if member:
                members = []
                for thread, deadline in threads.items():
                    embed.title = f'提出まで残り{str((deadline - datetime.datetime.now()).days)}日です！'
                    members.append(f'・ {thread.mention}')
                embed.description = '\n'.join(members)
                embed.color = discord.Color.yellow() if 0 < until <= 5 else discord.Color.red()
                await thread.send(embed=embed)
            else:
                logging.warning(f'Member {member_id} not found')

    async def notify_member_toggle(self, members: dict[discord.Member]) -> bool:
        toggle_result = [self.notify_db_handler.toggle_notify(member.id) for member in members]
        if all(toggle_result):
            return True
        else:
            return False

    async def get_threads(
        self,
        target_members: list[discord.Member],
        ) -> dict[str, dict[discord.Thread | None, datetime.datetime]]:

        thread_ids = {str(member.id): self.threads_db_handler.get_tagged_threads(str(member.id)) for member in target_members}
        # thread_idsが空の場合はNoneを返す
        _guild = self.interaction.guild if self.interaction else self.guild
        if not thread_ids.items() or not list(thread_ids.values())[0]:
            return None
        else:
            # thread_idsをthreadに変換, deadlineをdatetimeに変換
            threads = {
                member_id: {
                    _guild.get_thread(int(thread_id)): datetime.datetime.strptime(deadline, "%Y-%m-%d") for thread_id, deadline in threads.items()
                    } for member_id, threads in thread_ids.items()
                }
            return threads
    
    async def notify_member_db_sync(self) -> bool:
        '''success: True, failure: False'''
        try:
            members = self.interaction.guild.members if self.interaction else self.guild.members
            member_ids = [str(member.id) for member in members]
            db_member_ids = list(self.notify_db_handler.get_all_notify_states().keys())
            for member_id in member_ids:
                if member_id not in db_member_ids:
                    self.notify_db_handler.set_notify_state(member_id, True)
            return True
        except Exception as e:
            logging.error(f'Error syncing _notify member db: {e}')
            return False
    
    async def fetch_notifies(self) -> tuple[dict[str, dict[discord.Thread, datetime.datetime]]]:
        self.notify_member_db_sync(self.interaction if self.interaction else None, self.guild if self.guild else None)
        threads = await self.get_threads([self.guild.get_member(member_id) for member_id in self.notify_db_handler.get_notify_validity_members()], self.interaction)
        now = datetime.datetime.now()

        # thread内のdeadlineが5, 3, 1, 0日前のものを取得
        prior_notify_5days = {member_id: {thread: deadline for thread, deadline in threads[member_id].items() if (deadline - now).days == 5} for member_id in threads}
        prior_notify_3days = {member_id: {thread: deadline for thread, deadline in threads[member_id].items() if (deadline - now).days == 3} for member_id in threads}
        prior_notify_1day = {member_id: {thread: deadline for thread, deadline in threads[member_id].items() if (deadline - now).days == 1} for member_id in threads}
        very_day_notify = {member_id: {thread: deadline for thread, deadline in threads[member_id].items() if (deadline - now).days == 0} for member_id in threads}
        return tuple(prior_notify_5days, prior_notify_3days, prior_notify_1day, very_day_notify)
    
    # 毎日24時に実行
    @tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=datetime.timezone(datetime.timedelta(hours=9))))
    async def notify_very_day(self):
        notifies = self.fetch_notifies(self.interaction if self.interaction else self.guild)
        await self._notify(notifies[3], 0)
    
    # 毎日12時に実行
    @tasks.loop(time=datetime.time(hour=12, minute=0, tzinfo=datetime.timezone(datetime.timedelta(hours=9))))
    async def notify_prior(self):
        notifies = self.fetch_notifies(self.interaction if self.interaction else self.guild)
        await self._notify(notifies[0], 5)
        await self._notify(notifies[1], 3)
        await self._notify(notifies[2], 1)