import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging


class DatabaseConfigurationError(RuntimeError):
    """Raised when local database configuration is invalid or incomplete."""

class DatabaseConnection:
    def _get_connection_params(self):
        # Railway provides DATABASE_URL automatically
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return {'dsn': database_url}, 'DATABASE_URL'

        postgres_connection_string = os.getenv('POSTGRES_CONNECTION_STRING')
        if postgres_connection_string:
            return {'dsn': postgres_connection_string}, 'POSTGRES_CONNECTION_STRING'
        
        # Fallback for local development
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'rolebypost'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }, 'DB_*'

    def _describe_connection_target(self, connection_params: dict) -> str:
        if 'dsn' in connection_params:
            dsn = connection_params['dsn']
            scheme = 'postgresql'
            rest = dsn
            if '://' in dsn:
                scheme, rest = dsn.split('://', 1)

            try:
                credentials, host_and_db = rest.split('@', 1)
                user = credentials.split(':', 1)[0]
                return f"{scheme}://{user}:***@{host_and_db}"
            except ValueError:
                return f"{scheme}://***"

        user = connection_params.get('user', '<unknown>')
        host = connection_params.get('host', 'localhost')
        port = connection_params.get('port', '5432')
        database = connection_params.get('database', '<unknown>')
        return f"postgresql://{user}:***@{host}:{port}/{database}"

    def _raise_helpful_operational_error(self, error: psycopg2.OperationalError, connection_params: dict, source: str):
        message = str(error)
        safe_target = self._describe_connection_target(connection_params)

        if 'password authentication failed' in message.lower():
            raise DatabaseConfigurationError(
                "PostgreSQL authentication failed for the configured connection "
                f"({safe_target}, source={source}). "
                "Update your local database credentials in `.env` so `DATABASE_URL` "
                "(or `POSTGRES_CONNECTION_STRING` / `DB_*`) matches your real PostgreSQL username/password, then restart the bot."
            ) from error

        if 'does not exist' in message.lower() and 'database' in message.lower():
            raise DatabaseConfigurationError(
                "The configured PostgreSQL database does not exist for connection "
                f"({safe_target}, source={source}). "
                "Create the database first or point `.env` at an existing one, then restart the bot."
            ) from error

        raise error
    
    @contextmanager
    def get_connection(self):
        conn = None
        connection_params, source = self._get_connection_params()
        try:
            if 'dsn' in connection_params:
                conn = psycopg2.connect(connection_params['dsn'], cursor_factory=RealDictCursor)
            else:
                conn = psycopg2.connect(**connection_params, cursor_factory=RealDictCursor)
            yield conn
            conn.commit()
        except psycopg2.OperationalError as e:
            if conn:
                conn.rollback()
            logging.error(
                "Database connection failed for %s (source=%s): %s",
                self._describe_connection_target(connection_params),
                source,
                e,
            )
            self._raise_helpful_operational_error(e, connection_params, source)
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

db_manager = DatabaseConnection()