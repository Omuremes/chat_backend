from sqlalchemy import text

from app.core.config import get_settings
from app.db import models  # noqa: F401
from app.db.session import Base, engine


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _migrate_auth_user_columns() -> None:
    if engine.dialect.name != "postgresql":
        return

    query = text(
        """
        select tc.table_name, tc.constraint_name
        from information_schema.table_constraints tc
        join information_schema.key_column_usage kcu
          on tc.constraint_name = kcu.constraint_name
         and tc.table_schema = kcu.table_schema
        join information_schema.constraint_column_usage ccu
          on ccu.constraint_name = tc.constraint_name
         and ccu.table_schema = tc.table_schema
        where tc.constraint_type = 'FOREIGN KEY'
          and tc.table_schema = current_schema()
          and tc.table_name in ('conversation_participants', 'messages')
          and kcu.column_name in ('user_id', 'sender_id')
          and ccu.table_name = 'users'
        """
    )

    with engine.begin() as connection:
        existing_tables = {
            table_name
            for (table_name,) in connection.execute(
                text("select tablename from pg_tables where schemaname = current_schema()")
            )
        }
        if not {"conversation_participants", "messages"}.intersection(existing_tables):
            return

        for table_name, constraint_name in connection.execute(query):
            if table_name in {"conversation_participants", "messages"}:
                connection.execute(
                    text(
                        f"alter table {_quote_identifier(table_name)} "
                        f"drop constraint if exists {_quote_identifier(constraint_name)}"
                    )
                )

        if "conversation_participants" in existing_tables:
            connection.execute(
                text(
                    "alter table conversation_participants "
                    "alter column user_id type varchar(255) using user_id::varchar"
                )
            )
        if "messages" in existing_tables:
            connection.execute(
                text(
                    "alter table messages "
                    "alter column sender_id type varchar(255) using sender_id::varchar"
                )
            )


def init_db() -> None:
    if not get_settings().auto_create_tables:
        return
    _migrate_auth_user_columns()
    Base.metadata.create_all(bind=engine)
