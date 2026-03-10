import os
from typing import Optional
from contextlib import contextmanager
from mysql.connector import pooling, Error
from mysql.connector.pooling import MySQLConnectionPool

# Charger les variables d'environnement depuis .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv n'est pas installé, on continue sans
    pass


class DatabaseConnection:
    """Manages MySQL database connections with pooling."""
    
    _pool: Optional[MySQLConnectionPool] = None
    
    @classmethod
    def initialize(
        cls,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        pool_size: int = 5
    ):
        """Initialize the connection pool.
        
        Args:
            host: MySQL host (defaults to DB_HOST env var)
            port: MySQL port (defaults to DB_PORT env var or 3306)
            user: MySQL user (defaults to DB_USER env var)
            password: MySQL password (defaults to DB_PASSWORD env var)
            database: Database name (defaults to DB_NAME env var)
            pool_size: Connection pool size
        """
        config = {
            'host': host or os.getenv('DB_HOST', 'localhost'),
            'port': port or int(os.getenv('DB_PORT', 3306)),
            'user': user or os.getenv('DB_USER', 'root'),
            'password': password or os.getenv('DB_PASSWORD', 'changeme'),
            'database': database or os.getenv('DB_NAME', 'tap_db'),
            'pool_name': 'tap_pool',
            'pool_size': pool_size,
            'pool_reset_session': True,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': False
        }
        
        try:
            cls._pool = pooling.MySQLConnectionPool(**config)
            print(f"✅ Database connection pool initialized: {config['database']}@{config['host']}")
        except Error as e:
            error_code = e.errno if hasattr(e, 'errno') else None
            error_msg = str(e)
            
            # Si la base de données n'existe pas, essayer de la créer
            if error_code == 1049 or 'Unknown database' in error_msg:
                print(f"⚠️  Database '{config['database']}' not found. Attempting to create it...")
                try:
                    cls._create_database_if_not_exists(config)
                    # Réessayer de créer le pool après création de la base
                    cls._pool = pooling.MySQLConnectionPool(**config)
                    print(f"✅ Database '{config['database']}' created and connection pool initialized")
                except Exception as create_error:
                    print(f"❌ Failed to create database: {create_error}")
                    print(f"❌ Please create the database '{config['database']}' manually in phpMyAdmin")
                    raise
            else:
                print(f"❌ Error creating connection pool: {e}")
                print(f"   Host: {config['host']}, User: {config['user']}, Database: {config['database']}")
                raise
    
    @classmethod
    def _create_database_if_not_exists(cls, config: dict):
        """Create the database if it doesn't exist."""
        import mysql.connector
        
        # Se connecter sans spécifier la base de données
        temp_config = config.copy()
        temp_config.pop('database', None)
        temp_config.pop('pool_name', None)
        temp_config.pop('pool_size', None)
        temp_config.pop('pool_reset_session', None)
        temp_config.pop('autocommit', None)
        
        conn = mysql.connector.connect(**temp_config)
        cursor = conn.cursor()
        
        try:
            # Créer la base de données si elle n'existe pas
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{config['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            print(f"✅ Database '{config['database']}' created successfully")
        finally:
            cursor.close()
            conn.close()
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """Get a connection from the pool (context manager).
        
        Yields:
            MySQL connection object
            
        Raises:
            RuntimeError: If pool is not initialized
        """
        if cls._pool is None:
            cls.initialize()
        
        connection = cls._pool.get_connection()
        try:
            yield connection
            connection.commit()
        except Error as e:
            connection.rollback()
            raise
        finally:
            connection.close()
    
    @classmethod
    def get_connection_raw(cls):
        """Get a connection from the pool (manual management).
        
        Returns:
            MySQL connection object
            
        Raises:
            RuntimeError: If pool is not initialized
        """
        if cls._pool is None:
            cls.initialize()
        
        return cls._pool.get_connection()
    
    @classmethod
    def execute_query(cls, query: str, params: Optional[tuple] = None, fetch: bool = True):
        """Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results if fetch=True, else None
        """
        with cls.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            if fetch:
                results = cursor.fetchall()
                cursor.close()
                return results
            cursor.close()
            return None
    
    @classmethod
    def execute_many(cls, query: str, params_list: list):
        """Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            cursor.close()

