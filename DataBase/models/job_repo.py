from typing import Optional, List
import logging

from . import Job, JobType
from .. import get_db_cursor
from psycopg.rows import class_row

logger = logging.getLogger(__name__)

class JobRepository:
    _table_name = "jobs"
    _model = Job

    async def _execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False):
        factory = class_row(self._model)
        async with get_db_cursor(row_factory=factory) as cur:
            await cur.execute(query, params)
            if fetch_one:
                return await cur.fetchone()
            if fetch_all:
                return await cur.fetchall()
            return None

    async def get_by_id(self, job_id: int) -> Optional[Job]:
        query = f"SELECT * FROM public.{self._table_name} WHERE id = %s AND is_active = TRUE"
        try:
            return await self._execute_query(query, (job_id,), fetch_one=True)
        except Exception as e:
            logger.error(f"Error fetching job {job_id}: {e}", exc_info=True)
            return None

    async def get_active_jobs(self, job_type: Optional[JobType] = None, limit: int = 20, offset: int = 0) -> List[Job]:
        params = []
        where_clauses = ["is_active = TRUE"]
        if job_type:
            where_clauses.append("type = %s")
            params.append(job_type.value)

        where_sql = " AND ".join(where_clauses)
        params.extend([limit, offset])

        query = f"SELECT * FROM public.{self._table_name} WHERE {where_sql} ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s"
        try:
            return await self._execute_query(query, tuple(params), fetch_all=True) or []
        except Exception as e:
            logger.error(f"Error fetching active jobs: {e}", exc_info=True)
            return []