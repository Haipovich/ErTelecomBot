from typing import Optional
import logging
from datetime import datetime

from psycopg.rows import class_row

from . import ActivityReminder, ReminderType 
from .. import get_db_cursor 

logger = logging.getLogger(__name__)

class ActivityReminderRepository:
    _table_name = "activity_reminders"
    _model = ActivityReminder

    async def _execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False, row_factory: type = None):
        factory = row_factory if row_factory else class_row(self._model)
        async with get_db_cursor(row_factory=factory) as cur:
            await cur.execute(query, params)
            if fetch_one:
                return await cur.fetchone()
            if fetch_all:
                return await cur.fetchall()
            return cur.rowcount if cur.rowcount != -1 else None 

    async def add_reminder_sent(self, user_id: int, activity_id: int, reminder_type: ReminderType) -> Optional[ActivityReminder]:
        query = (
            f"INSERT INTO public.{self._table_name} (user_id, activity_id, reminder_type, sent_at) "
            f"VALUES (%s, %s, %s, %s) RETURNING *"
        )
        params = (user_id, activity_id, reminder_type.value, datetime.utcnow())
        try:
            created_reminder = await self._execute_query(query, params, fetch_one=True)
            if created_reminder:
                logger.info(f"Reminder {reminder_type.value} for activity {activity_id} to user {user_id} marked as sent.")
            return created_reminder
        except Exception as e:
            logger.error(f"Error adding reminder entry for user {user_id}, activity {activity_id}, type {reminder_type.value}: {e}", exc_info=True)
            return None

    async def has_reminder_been_sent(self, user_id: int, activity_id: int, reminder_type: ReminderType) -> bool:
        query = f"SELECT EXISTS (SELECT 1 FROM public.{self._table_name} WHERE user_id = %s AND activity_id = %s AND reminder_type = %s)"
        params = (user_id, activity_id, reminder_type.value)
        try:
            async with get_db_cursor() as cur: 
                await cur.execute(query, params)
                result = await cur.fetchone()
                return result[0] if result else False
        except Exception as e:
            logger.error(f"Error checking if reminder was sent for user {user_id}, activity {activity_id}, type {reminder_type.value}: {e}", exc_info=True)
            return False 

    async def delete_reminder(self, user_id: int, activity_id: int, reminder_type: ReminderType) -> bool:
        query = f"DELETE FROM public.{self._table_name} WHERE user_id = %s AND activity_id = %s AND reminder_type = %s"
        params = (user_id, activity_id, reminder_type.value)
        try:
            rows_affected = await self._execute_query(query, params, row_factory=None) 
            deleted = rows_affected is not None and rows_affected > 0
            if deleted:
                logger.info(f"Reminder entry for user {user_id}, activity {activity_id}, type {reminder_type.value} deleted from DB.")
            else:
                logger.info(f"No reminder entry found in DB to delete for user {user_id}, activity {activity_id}, type {reminder_type.value}.")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting reminder entry from DB for user {user_id}, activity {activity_id}, type {reminder_type.value}: {e}", exc_info=True)
            return False 
