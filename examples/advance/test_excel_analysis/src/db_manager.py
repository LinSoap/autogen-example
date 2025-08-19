import duckdb
import pandas as pd


# Singleton-like DuckDB connection manager
class DuckDBManager:
    _connection = None

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            cls._connection = duckdb.connect()
        return cls._connection

    @classmethod
    def register_dataframe(cls, df: pd.DataFrame, table_name: str):
        """Register a DataFrame as a table in DuckDB with the given table name."""
        con = cls.get_connection()
        con.register(table_name, df)
        return table_name

    @classmethod
    def query(cls, query: str) -> pd.DataFrame:
        """Execute a query and return results as a DataFrame."""
        con = cls.get_connection()
        return con.execute(query).df()

    @classmethod
    def list_tables(cls) -> list:
        """List all available tables in the DuckDB connection."""
        con = cls.get_connection()
        result = con.execute("SHOW TABLES").fetchall()
        return [row[0] for row in result]

    @classmethod
    def close(cls):
        """Close the DuckDB connection."""
        if cls._connection is not None:
            cls._connection.close()
            cls._connection = None
