import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / 'secret.env'
print(f"Loading environment variables from: {env_path}")

if env_path.is_file():
    load_dotenv(dotenv_path=env_path)
    print(".env file loaded.")
else:
    print(f"Warning: .env file not found at {env_path}. Attempting to use system environment variables.")

@dataclass
class BotConfig:
    token: str

@dataclass
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    name: str

    @property
    def dsn_psycopg(self) -> str:
        """DSN строка для psycopg."""
        return (f"host={self.host} port={self.port} "
                f"dbname={self.name} user={self.user} "
                f"password={self.password}")

@dataclass
class Config:
    bot: BotConfig
    db: DbConfig

def load_config() -> Config:
    try:
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN environment variable not set.")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = int(os.getenv("DB_PORT", 5432))
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME")
        if not all([db_user, db_password, db_name]):
             raise ValueError("One or more DB environment variables (DB_USER, DB_PASSWORD, DB_NAME) are missing.")
        return Config(
            bot=BotConfig(token=bot_token),
            db=DbConfig(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                name=db_name
            )
        )
    except ValueError as e:
        print(f"Error loading configuration: {e}")
        exit(f"Configuration Error: {e}")
    except Exception as e:
         print(f"An unexpected error occurred during config loading: {e}")
         exit("Unexpected configuration error.")
config = load_config()