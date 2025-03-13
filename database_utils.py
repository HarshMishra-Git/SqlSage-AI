import os
import psycopg2
from psycopg2 import sql

def get_db_connection():
    """
    Create a connection to the PostgreSQL database using environment variables.
    
    :return: Database connection object
    """
    conn = psycopg2.connect(
        dbname=os.environ.get("PGDATABASE", "postgres"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", "12345"),
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432")
    )
    conn.autocommit = True
    return conn

def list_all_tables():
    """
    List all tables in the database.
    
    :return: List of table names
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = cursor.fetchall()
        return [table[0] for table in tables]
    finally:
        cursor.close()
        conn.close()

def get_table_schema(table_name):
    """
    Get schema information for a specific table.
    
    :param table_name: Name of the table
    :return: Dictionary with column names and data types
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get column information
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """)
        columns = cursor.fetchall()
        
        # Get primary key information
        cursor.execute(f"""
            SELECT c.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name)
            JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema
                AND tc.table_name = c.table_name AND ccu.column_name = c.column_name
            WHERE constraint_type = 'PRIMARY KEY' AND tc.table_name = '{table_name}'
        """)
        primary_keys = [pk[0] for pk in cursor.fetchall()]
        
        # Get foreign key information
        cursor.execute(f"""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = '{table_name}'
        """)
        foreign_keys = [
            {
                'column': fk[0],
                'foreign_table': fk[1],
                'foreign_column': fk[2]
            }
            for fk in cursor.fetchall()
        ]
        
        return {
            'columns': {
                col[0]: {
                    'data_type': col[1],
                    'is_nullable': col[2],
                    'default': col[3]
                }
                for col in columns
            },
            'primary_keys': primary_keys,
            'foreign_keys': foreign_keys
        }
    finally:
        cursor.close()
        conn.close()

def load_database_schema():
    """
    Load the complete database schema including all tables.
    
    :return: Dictionary with all table schemas
    """
    all_tables = list_all_tables()
    schema = {}
    
    for table in all_tables:
        schema[table] = get_table_schema(table)
    
    return schema

def verify_query(query):
    """
    Check if a SQL query is valid by parsing it with PostgreSQL.
    Note: This doesn't execute the query, it just checks its syntax.
    
    :param query: SQL query to verify
    :return: Tuple (is_valid, error_message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Parse the query without executing it
        cursor.execute(f"""
            PREPARE verify_stmt AS
            {query}
        """)
        cursor.execute("DEALLOCATE verify_stmt")
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def explain_query(query):
    """
    Get the execution plan for a SQL query.
    
    :param query: SQL query to explain
    :return: Tuple (success, explanation or error)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"EXPLAIN {query}")
        return True, cursor.fetchall()
    except Exception as e:
        return False, str(e)
    finally:
        cursor.close()
        conn.close()
