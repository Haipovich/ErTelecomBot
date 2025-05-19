from typing import Optional, List, Dict, Any
import logging
from psycopg import errors as psycopg_errors
from psycopg.rows import dict_row, class_row
import asyncio
from aiogram import Bot

from . import Application, ApplicationCreate, ApplicationStatus, Activity
from .activity_repo import ActivityRepository
from .. import get_db_cursor

logger = logging.getLogger(__name__)

class ApplicationRepository:
    _table_name = "applications"
    _model = Application

    async def _execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False, row_factory: type = None):
        factory = row_factory if row_factory else class_row(self._model)
        async with get_db_cursor(row_factory=factory) as cur:
            await cur.execute(query, params)
            if fetch_one:
                return await cur.fetchone()
            if fetch_all:
                return await cur.fetchall()
            return cur.rowcount if cur.rowcount != -1 else None

    async def add(self, app_data: ApplicationCreate) -> Optional[Application]:
        existing_app = await self.get_by_user_and_target(
            user_id=app_data.user_id,
            job_id=app_data.job_id,
            activity_id=app_data.activity_id
        )

        if existing_app:
             logger.warning(f"User {app_data.user_id} already has an active application {existing_app.id} for this target.")
             return existing_app

        data_dict = app_data.model_dump(exclude_unset=True)
        fields = ', '.join(data_dict.keys())
        placeholders = ', '.join(['%s'] * len(data_dict))
        values = tuple(data_dict.values())
        query = (
            f"INSERT INTO public.{self._table_name} ({fields}) "
            f"VALUES ({placeholders}) RETURNING *"
        )
        try:
            created_app = await self._execute_query(query, values, fetch_one=True, row_factory=class_row(self._model))
            if created_app:
                logger.info(f"Application {created_app.id} created by user {created_app.user_id}.")
                return created_app
            else:
                 logger.error(f"Failed to retrieve created application data for user {app_data.user_id}.")
                 return None
        except psycopg_errors.ForeignKeyViolation as e:
             logger.error(f"Error adding application for user {app_data.user_id}: Foreign key violation. {e}")
             return None
        except Exception as e:
            logger.error(f"Error adding application for user {app_data.user_id}: {e}", exc_info=True)
            return None

    async def get_by_id_and_user(self, app_id: int, user_id: int) -> Optional[Application]:
        query = f"SELECT * FROM public.{self._table_name} WHERE id = %s AND user_id = %s"
        try:
            return await self._execute_query(query, (app_id, user_id), fetch_one=True, row_factory=class_row(self._model))
        except Exception as e:
            logger.error(f"Error fetching application {app_id} for user {user_id}: {e}", exc_info=True)
            return None

    async def get_user_applications_with_details(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        query = """
            SELECT
                app.id, app.status, app.application_time, app.job_id, app.activity_id,
                COALESCE(j.title, act.title, 'Неизвестная цель') AS target_title
            FROM public.applications app
            LEFT JOIN public.jobs j ON app.job_id = j.id
            LEFT JOIN public.activities act ON app.activity_id = act.id
            WHERE app.user_id = %s
            ORDER BY app.application_time DESC
            LIMIT %s OFFSET %s;
        """
        params = (user_id, limit, offset)
        try:
            results = await self._execute_query(query, params, fetch_all=True, row_factory=dict_row)
            if results:
                for row in results:
                     if 'status' in row and isinstance(row['status'], str):
                         try: row['status'] = ApplicationStatus(row['status'])
                         except ValueError: logger.warning(f"Unknown status '{row['status']}' for app {row.get('id')}")
            return results or []
        except Exception as e:
            logger.error(f"Error fetching applications with details for user {user_id}: {e}", exc_info=True)
            return []

    async def get_by_user_and_target(self, user_id: int, job_id: Optional[int] = None, activity_id: Optional[int] = None) -> Optional[Application]:
         if job_id is not None:
             query = f"SELECT * FROM public.{self._table_name} WHERE user_id = %s AND job_id = %s"
             params = (user_id, job_id)
         elif activity_id is not None:
             query = f"SELECT * FROM public.{self._table_name} WHERE user_id = %s AND activity_id = %s"
             params = (user_id, activity_id)
         else:
             return None
         try:
             return await self._execute_query(query, params, fetch_one=True, row_factory=class_row(self._model))
         except Exception as e:
              logger.error(f"Error checking application for user {user_id}, target job={job_id}, activity={activity_id}: {e}", exc_info=True)
              return None

    async def delete_by_user(self, app_id: int, user_id: int) -> bool:
        current_app = await self.get_by_id_and_user(app_id, user_id)
        if not current_app:
            logger.warning(f"Application {app_id} not found or does not belong to user {user_id} for deletion.")
            return False
        allowed_statuses_for_deletion = [ApplicationStatus.PENDING, ApplicationStatus.UNDER_REVIEW]
        if current_app.status not in allowed_statuses_for_deletion:
             logger.warning(f"Application {app_id} cannot be deleted by user {user_id} due to current status: {current_app.status}")
             return False
        query = f"DELETE FROM public.{self._table_name} WHERE id = %s AND user_id = %s"
        try:
            rows_affected = await self._execute_query(query, (app_id, user_id), row_factory=None)
            deleted = rows_affected is not None and rows_affected > 0
            if deleted:
                logger.info(f"Application {app_id} deleted by user {user_id}.")
            else:
                logger.warning(f"Application {app_id} was not found during deletion for user {user_id} (maybe deleted concurrently?).")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting application {app_id} for user {user_id}: {e}", exc_info=True)
            return False

    async def update_status_and_comment(
        self,
        application_id: int,
        new_status: ApplicationStatus,
        hr_comment: Optional[str] = None
    ) -> bool:
        set_parts = ["status = %s"]
        params = [new_status.value]

        if hr_comment is not None:
            set_parts.append("hr_comment = %s")
            params.append(hr_comment)
        else: 
             set_parts.append("hr_comment = NULL")


        set_clause = ", ".join(set_parts)
        params.append(application_id)

        query = (
            f"UPDATE public.{self._table_name} "
            f"SET {set_clause}, updated_at = NOW() "
            f"WHERE id = %s"
        )
        try:
            rows_affected = await self._execute_query(query, tuple(params), row_factory=None)
            updated = rows_affected is not None and rows_affected > 0
            if updated:
                logger.info(f"Application {application_id} status updated to {new_status}, hr_comment processed.")
            else:
                logger.warning(f"Application {application_id} not found or not updated for status/comment change.")
            return updated
        except Exception as e:
            logger.error(f"Error updating status/comment for application {application_id}: {e}", exc_info=True)
            return False

    async def get_application_details_for_notification(self, application_id: int) -> Optional[dict]:
        query = """
            SELECT
                app.id, app.user_id, app.status, app.hr_comment,
                COALESCE(j.title, act.title, 'Неизвестная цель') AS target_title,
                app.job_id, app.activity_id
            FROM public.applications app
            LEFT JOIN public.jobs j ON app.job_id = j.id
            LEFT JOIN public.activities act ON app.activity_id = act.id
            WHERE app.id = %s;
        """
        try:
            result = await self._execute_query(query, (application_id,), fetch_one=True, row_factory=dict_row)
            if result and 'status' in result and isinstance(result['status'], str):
                 try:
                     result['status'] = ApplicationStatus(result['status'])
                 except ValueError:
                     logger.warning(f"Unknown status '{result['status']}' for app_id {result.get('id')} in get_application_details_for_notification")
            return result
        except Exception as e:
            logger.error(f"Error fetching application details for notification (app_id {application_id}): {e}", exc_info=True)
            return None

    async def get_user_ids_for_activity(self, activity_id: int) -> List[int]:
        query = f"SELECT DISTINCT user_id FROM public.{self._table_name} WHERE activity_id = %s"
        params = (activity_id,)
        user_ids = []
        try:
            results = await self._execute_query(query, params, fetch_all=True, row_factory=dict_row)
            if results:
                user_ids = [row['user_id'] for row in results]
            logger.debug(f"Found {len(user_ids)} users for activity {activity_id}: {user_ids}")
            return user_ids
        except Exception as e:
            logger.error(f"Error fetching user IDs for activity {activity_id}: {e}", exc_info=True)
            return []
