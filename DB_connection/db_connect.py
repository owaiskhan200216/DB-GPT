from config import DatabaseConfig
from langchain_community.utilities.sql_database import SQLDatabase
from db_connection_uri import create_database_uri


def db_connect(config: DatabaseConfig):
    db_uri = create_database_uri(config)
    db = SQLDatabase.from_uri(db_uri, include_tables=config.table_names)
    return db
