import sys
import os
import uuid
# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import create_shop, get_db_session
from app.database import models

def test():
    print("--- Starting Shop/Staff Simulation ---")
    
    # 1. Need an owner
    db = get_db_session()
    owner = db.query(models.User).filter(models.User.role == 'OWNER').first()
    if not owner:
        print("Creating dummy owner...")
        owner = models.User(
            name="Test Owner",
            email=f"test_owner_{uuid.uuid4().hex[:4]}@test.com",
            phone="0000000000",
            password="hashed",
            role="OWNER"
        )
        db.add(owner)
        db.flush()
    
    owner_id = owner.id
    db.close()

    # 2. Mock shop data
    shop_data = {
        "name": "Simulation Shop",
        "address": "123 Test St",
        "description": "Verification shop",
        "coordinates": {"lat": 0.0, "lng": 0.0},
        "ownerId": owner_id,
        "phone": "1111111111",
        "email": "sim@test.com",
        "services": [
            {"name": "Sim Service", "price": 50, "duration": 30}
        ],
        "staff": [
            {"name": "Sim Staff", "phone": "9999999999"}
        ]
    }

    print(f"Calling create_shop with owner: {owner_id}")
    result = create_shop(shop_data)
    
    if result:
        print("✅ Shop created successfully!")
        print(f"Resulting staff count in hydration: {len(result.get('staff', []))}")
    else:
        print("❌ Shop creation failed (returned None).")

if __name__ == "__main__":
    test()
