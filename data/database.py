import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging

class DatabaseConnection:
    def __init__(self):
        self.connection_params = self._get_connection_params()
    
    def _get_connection_params(self):
        # Railway provides DATABASE_URL automatically
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return {'dsn': database_url}
        
        # Fallback for local development
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'playbypostbot'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            if 'dsn' in self.connection_params:
                conn = psycopg2.connect(self.connection_params['dsn'], cursor_factory=RealDictCursor)
            else:
                conn = psycopg2.connect(**self.connection_params, cursor_factory=RealDictCursor)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

db_manager = DatabaseConnection()