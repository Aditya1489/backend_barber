from app.database.database import SessionLocal
from app.database import models

def check_notifs():
    db = SessionLocal()
    try:
        notifs = db.query(models.Notification).all()
        print(f"Total notifications in DB: {len(notifs)}")
        for n in notifs:
            print(f"ID: {n.id}, UserID: {n.userId}, Title: {n.title}, IsRead: {n.isRead}")
    finally:
        db.close()

if __name__ == "__main__":
    check_notifs()
