from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Type, Any
from psycopg.rows import class_row, dict_row
from pydantic import BaseModel

from .. import get_db_cursor

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseRepository(ABC, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):

    def __init__(self, model: Type[ModelType]):
        self._model = model

    @property
    @abstractmethod
    def _table_name(self) -> str:
        pass

    async def _execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False, model_factory: bool = True):
        factory = class_row(self._model) if model_factory and self._model else dict_row
        async with get_db_cursor(row_factory=factory) as cur:
            await cur.execute(query, params)
            if fetch_one:
                return await cur.fetchone()
            if fetch_all:
                return await cur.fetchall()
            return cur.rowcount if cur.rowcount != -1 else None

    async def get_by_id(self, item_id: Any) -> Optional[ModelType]:
        query = f"SELECT * FROM public.{self._table_name} WHERE id = %s"
        return await self._execute_query(query, (item_id,), fetch_one=True)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        query = f"SELECT * FROM public.{self._table_name} ORDER BY id LIMIT %s OFFSET %s"
        return await self._execute_query(query, (limit, offset), fetch_all=True)

    @abstractmethod
    async def add(self, item_data: CreateSchemaType) -> Optional[ModelType]:
        pass

    @abstractmethod
    async def update(self, item_id: Any, item_data: UpdateSchemaType) -> Optional[ModelType]:
        pass