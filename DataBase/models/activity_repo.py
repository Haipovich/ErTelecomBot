from typing import Optional, List
import logging

from . import Activity
from .. import get_db_cursor
from psycopg.rows import class_row

logger = logging.getLogger(__name__)

class ActivityRepository:
    _table_name = "activities"
    _model = Activity

    async def _execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False):
        factory = class_row(self._model)
        async with get_db_cursor(row_factory=factory) as cur:
            await cur.execute(query, params)
            if fetch_one:
                return await cur.fetchone()
            if fetch_all:
                return await cur.fetchall()
            return None

    async def get_by_id(self, activity_id: int) -> Optional[Activity]:
        query = f"SELECT * FROM public.{self._table_name} WHERE id = %s AND is_active = TRUE AND end_time >= NOW()"
        try:
            return await self._execute_query(query, (activity_id,), fetch_one=True)
        except Exception as e:
            logger.error(f"Error fetching activity {activity_id}: {e}", exc_info=True)
            return None

    async def get_active_activities(self, upcoming_only: bool = True, limit: int = 20, offset: int = 0) -> List[Activity]:
        params = []
        where_clauses = ["is_active = TRUE"]
        if upcoming_only:
            where_clauses.append("end_time >= NOW()")
        where_sql = " AND ".join(where_clauses)
        params.extend([limit, offset])
        query = f"SELECT * FROM public.{self._table_name} WHERE {where_sql} ORDER BY start_time ASC, id ASC LIMIT %s OFFSET %s"
        try:
            return await self._execute_query(query, tuple(params), fetch_all=True) or []
        except Exception as e:
            logger.error(f"Error fetching active activities: {e}", exc_info=True)
            return []