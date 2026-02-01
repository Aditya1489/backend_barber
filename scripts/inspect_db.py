import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database.database import engine
from sqlalchemy import inspect

def inspect_db():
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        print(f"Table: {table_name}")
        for column in inspector.get_columns(table_name):
            print(f"  - {column['name']} ({column['type']})")

if __name__ == "__main__":
    inspect_db()
