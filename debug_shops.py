from app.database.database import SessionLocal
from app.database import models

db = SessionLocal()
shops = db.query(models.Shop).all()

print(f"Found {len(shops)} shops:")
for s in shops:
    print(f"Shop: {s.name} (ID: {s.id})")
    print(f"  > Photos: {s.photos}")
    print(f"  > Owner ID: {s.ownerId}")

db.close()
