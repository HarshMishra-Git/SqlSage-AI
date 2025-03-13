import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database connection info from environment variables
db_url = os.environ.get("DATABASE_URL")

def load_sql_file(file_path):
    """
    Load the SQL file and execute it on the database.
    
    :param file_path: Path to the SQL file
    """
    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Read SQL file
        with open(file_path, 'r') as f:
            sql = f.read()
        
        # Execute SQL
        cursor.execute(sql)
        
        print("Successfully created tables from SQL file!")
        
        # Close connection
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    load_sql_file("attached_assets/hackathon_database_iitd.sql")