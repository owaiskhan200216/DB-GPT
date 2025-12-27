from urllib.parse import quote_plus
from config import DatabaseConfig


def create_database_uri(config: DatabaseConfig) -> str:
    """Create database URI based on database type and configuration"""
    db_type = config.db_type.lower()

    if db_type == "sqlite":
        # For SQLite, db_name should be the file path
        return f"sqlite:///{config.db_name}"

    elif db_type == "mysql":
        port = config.db_port or 3306
        password = quote_plus(config.db_password)
        return f"mysql+pymysql://{config.db_user}:{password}@{config.db_host}:{port}/{config.db_name}"

    elif db_type == "postgresql":
        port = config.db_port or 5432
        password = quote_plus(config.db_password)
        return f"postgresql+psycopg2://{config.db_user}:{password}@{config.db_host}:{port}/{config.db_name}"

    elif db_type == "oracle":
        port = config.db_port or 1521
        return f"oracle+cx_oracle://{config.db_user}:{config.db_password}@{config.db_host}:{port}/{config.db_name}"

    elif db_type == "mssql":
        port = config.db_port or 1433
        return f"mssql+pyodbc://{config.db_user}:{config.db_password}@{config.db_host} /{config.db_name}?driver=ODBC+Driver+17+for+SQL+Server"

    else:
        raise ValueError(f"Unsupported database type: {db_type}")
