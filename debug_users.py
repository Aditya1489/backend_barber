from app.database.database import SessionLocal
from app.database import models

db = SessionLocal()
users = db.query(models.User).all()

print(f"Found {len(users)} users:")
for u in users:
    if u.portfolio:
        print(f"User: {u.name} (ID: {u.id})")
        print(f"  > Portfolio: {u.portfolio}")

db.close()
