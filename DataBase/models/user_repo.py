from typing import Optional
import logging
from psycopg import errors as psycopg_errors

from . import User, UserCreate, UserUpdate
from .. import get_db_cursor
from psycopg.rows import class_row

logger = logging.getLogger(__name__)

class UserRepository:
    _table_name = "users"
    _model = User

    async def _execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False, model_factory: bool = True):
        factory = class_row(self._model) if model_factory and self._model else None
        async with get_db_cursor(row_factory=factory) as cur:
            await cur.execute(query, params)
            if fetch_one:
                return await cur.fetchone()
            if fetch_all:
                return await cur.fetchall()
            return cur.rowcount if cur.rowcount != -1 else None

    async def get_by_id(self, user_id: int) -> Optional[User]:
        query = f"SELECT * FROM public.{self._table_name} WHERE id = %s"
        return await self._execute_query(query, (user_id,), fetch_one=True)

    async def add(self, user_data: UserCreate) -> Optional[User]:
        data_dict = user_data.model_dump(exclude_unset=True)
        fields = ', '.join(data_dict.keys())
        placeholders = ', '.join(['%s'] * len(data_dict))
        values = tuple(data_dict.values())

        query = (
            f"INSERT INTO public.{self._table_name} ({fields}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT (id) DO NOTHING "
            f"RETURNING *"
        )
        try:
            created_user = await self._execute_query(query, values, fetch_one=True)
            if created_user:
                 logger.info(f"User profile for {created_user.id} created.")
            else:
                 logger.warning(f"User profile for {user_data.id} already exists.")
                 return await self.get_by_id(user_data.id)
            return created_user
        except psycopg_errors.UniqueViolation as e:
             logger.error(f"Error adding user {user_data.id}: Unique constraint violated. {e}")
             return None
        except Exception as e:
            logger.error(f"Error adding user {user_data.id}: {e}", exc_info=True)
            return None

    async def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        data_dict = user_data.model_dump(exclude_unset=True)

        if not data_dict:
            logger.warning(f"User {user_id} update called with no data.")
            return await self.get_by_id(user_id)

        set_clause = ', '.join([f"{key} = %s" for key in data_dict.keys()])
        values = tuple(data_dict.values()) + (user_id,)

        query = (
            f"UPDATE public.{self._table_name} SET {set_clause} "
            f"WHERE id = %s RETURNING *"
        )
        try:
            updated_user = await self._execute_query(query, values, fetch_one=True)
            if updated_user:
                logger.info(f"User profile {user_id} updated successfully.")
            else:
                logger.warning(f"User profile {user_id} not found for update.")
            return updated_user
        except psycopg_errors.UniqueViolation as e:
             logger.error(f"Error updating user {user_id}: Unique constraint violated (e.g., email/phone taken). {e}")
             return None
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}", exc_info=True)
            return None