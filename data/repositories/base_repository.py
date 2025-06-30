from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional
from data.database import db_manager

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    def __init__(self, table_name: str):
        self.table_name = table_name
    
    @abstractmethod
    def to_dict(self, entity: T) -> dict:
        """Convert entity to dictionary for database storage"""
        pass
    
    @abstractmethod
    def from_dict(self, data: dict) -> T:
        """Convert dictionary from database to entity"""
        pass
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        """Execute a query and return results"""
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                
                if fetch_one:
                    result = cur.fetchone()
                    return self.from_dict(dict(result)) if result else None
                elif fetch_all:
                    results = cur.fetchall()
                    return [self.from_dict(dict(row)) for row in results]
                else:
                    return cur.rowcount
    
    def find_by_id(self, id_column: str, id_value: str) -> Optional[T]:
        """Find entity by ID"""
        query = f"SELECT * FROM {self.table_name} WHERE {id_column} = %s"
        return self.execute_query(query, (id_value,), fetch_one=True)
    
    def find_all_by_column(self, column: str, value: str) -> List[T]:
        """Find all entities by column value"""
        query = f"SELECT * FROM {self.table_name} WHERE {column} = %s"
        return self.execute_query(query, (value,), fetch_all=True)
    
    def save(self, entity: T, conflict_columns: List[str] = None) -> None:
        """Save entity with upsert logic"""
        data = self.to_dict(entity)
        columns = list(data.keys())
        placeholders = ['%s'] * len(columns)
        values = list(data.values())
        
        query = f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        
        if conflict_columns:
            # Add ON CONFLICT DO UPDATE for PostgreSQL
            conflict_cols = ', '.join(conflict_columns)
            
            # Only include columns that are NOT in the conflict columns for the UPDATE
            update_columns = [col for col in columns if col not in conflict_columns]
            
            if update_columns:
                # There are columns to update
                update_cols = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_columns])
                query += f" ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_cols}"
            else:
                # All columns are part of the primary key/conflict, so just ignore duplicates
                query += f" ON CONFLICT ({conflict_cols}) DO NOTHING"
        
        self.execute_query(query, tuple(values))
    
    def delete(self, where_clause: str, params: tuple = None) -> int:
        """Delete entities matching where clause"""
        query = f"DELETE FROM {self.table_name} WHERE {where_clause}"
        return self.execute_query(query, params)