from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

import psycopg
from psycopg_pool import AsyncConnectionPool

try:
    from config import config as app_config
except ImportError:
    print("Error: Could not import 'config' from the root directory.")
    print("Make sure main.py and the DataBase directory are in the same root folder,")
    print("and you are running the script from the root folder.")
    app_config = None

_db_pool: Optional[AsyncConnectionPool] = None

async def init_db_pool():
    global _db_pool
    if _db_pool is None and app_config and app_config.db:
        print("Initializing database connection pool...")
        temp_pool = None
        try:
            temp_pool = AsyncConnectionPool(
                conninfo=app_config.db.dsn_psycopg,
                min_size=1,
                max_size=10,
            )
            print("Opening connection pool...")
            await temp_pool.open(wait=True)
            print("Pool opened. Testing connection...")

            async with temp_pool.connection() as conn:
                 async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    result = await cur.fetchone()
                    if result and result[0] == 1:
                        _db_pool = temp_pool
                        print("Database connection pool initialized and tested successfully.")
                    else:
                         print("Database connection test failed after pool opening.")
                         await temp_pool.close()
                         _db_pool = None
        except Exception as e:
            print(f"Failed to initialize database pool: {e}")
            if temp_pool:
                await temp_pool.close()
            _db_pool = None
    elif _db_pool:
        print("Database pool already initialized.")
    elif not app_config or not app_config.db:
         print("Database configuration not loaded, cannot initialize pool.")
    else:
        print("Attempted to initialize pool, but it's already None (previous error?).")


def get_db_pool() -> AsyncConnectionPool:
    if _db_pool is None:
        raise RuntimeError("Database pool is not initialized. Check initialization logs.")
    return _db_pool

@asynccontextmanager
async def get_db_cursor(row_factory=None) -> AsyncGenerator:
    pool = get_db_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=row_factory) as cur:
            yield cur

async def close_db_pool():
    global _db_pool
    if _db_pool:
        print("Closing database connection pool...")
        await _db_pool.close()
        _db_pool = None
        print("Database connection pool closed.")

async def get_dedicated_db_connection():
    if not app_config or not app_config.db:
        raise RuntimeError("Database configuration not loaded, cannot create dedicated connection.")
    try:
        conn = await psycopg.AsyncConnection.connect(app_config.db.dsn_psycopg, autocommit=True)
        return conn
    except Exception as e:
        print(f"Error creating dedicated DB connection: {e}")
        return None
