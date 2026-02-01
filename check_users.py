from app.database.database import SessionLocal
from app.database import models

def check_users():
    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        print(f"Total users in DB: {len(users)}")
        for u in users:
            print(f"ID: {u.id}, Name: {u.name}, Email: {u.email}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
