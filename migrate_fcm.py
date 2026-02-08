from sqlalchemy import create_engine, text
import sys

DATABASE_URL = "postgresql://adityachavhan@localhost/barbersync"

def migrate():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS "fcmToken" VARCHAR;'))
            conn.commit()
            print("✅ Successfully added fcmToken column to users table")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
