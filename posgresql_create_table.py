import os
from sqlalchemy import create_engine, text
from sqlmodel import SQLModel
import sys
import time

# --- IMPORTANT: Adjust this import path if necessary ---
try:
    from app.models import User, Item, DefaultCard, AddReplyCard, Cookie, ReplyLike
except ImportError as e:
    print(f"Error importing models: {e}")
    sys.exit(1)

def get_database_url():
    """Constructs the database URL using hardcoded values."""
    pg_user = "postgres"
    pg_password = "yfz200504"
    pg_server = "localhost"  # 容器名称
    pg_port = "5432"
    pg_db = "app"

    return f"postgresql://{pg_user}:{pg_password}@{pg_server}:{pg_port}/{pg_db}"

def create_db_and_tables():
    """Creates the database engine and then all tables defined by SQLModel."""
    db_url = get_database_url()
    pg_db = "app"  # Define pg_db here to fix the undefined variable error
    print(f"Attempting to connect to database: {db_url}")

    engine = create_engine(db_url, echo=False)  # Set echo=True for verbose SQL output

    # Retry logic for connecting to the database
    max_retries = 10  # Maximum number of retries
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                # Check if the specific database exists by trying a simple query
                connection.execute(text("SELECT 1"))
                print(f"Successfully connected to database '{pg_db}'.")
                break  # Exit the loop if connection is successful
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)  # Wait before retrying
            else:
                print("Max retries reached. Exiting.")
                return

    print("\nChecking if tables exist...")
    try:
        # Check if any of our tables already exist
        with engine.connect() as connection:
            # Get list of all tables in the database
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            existing_tables = {row[0] for row in result}
            
            # Check if any of our model tables exist
            model_tables = {model.__tablename__ for model in [User, Item, DefaultCard, AddReplyCard, Cookie, ReplyLike]}
            existing_model_tables = existing_tables.intersection(model_tables)
            
            if existing_model_tables:
                print(f"Found existing tables: {', '.join(existing_model_tables)}")
                print("Tables already exist, skipping creation.")
                return
            
            print("No existing tables found. Creating tables...")
            # SQLModel.metadata.create_all will issue CREATE TABLE IF NOT EXISTS statements
            SQLModel.metadata.create_all(engine)
            print("Tables created successfully.")
    except Exception as e:
        print(f"Error checking/creating tables: {e}")

if __name__ == "__main__":
    print("--- Database Table Creation Script for SQLModel ---")
    print("This script will attempt to connect to your PostgreSQL database")
    print("and create tables based on your SQLModel definitions.")
    print("\nPrerequisites:")
    print("  - PostgreSQL server must be running.")
    print("  - The target database must already exist on the server.")
    print("  - Required Python packages: sqlmodel, psycopg2-binary.")
    print("-" * 50)

    create_db_and_tables()
    print("-" * 50)
    print("Script finished.")
