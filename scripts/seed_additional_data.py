import sys
import os
import uuid
import bcrypt
from datetime import datetime

# Add the project root to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.database import SessionLocal
from app.database import models

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def seed_data():
    db = SessionLocal()
    try:
        print("Starting Seeding Additional Data...")
        
        # 1. Create Owners
        owners_data = [
            {
                "name": "Alex Rivera",
                "email": "alex@riveracuts.com",
                "phone": "+15559901",
                "role": "OWNER"
            },
            {
                "name": "Sarah Chen",
                "email": "sarah@chencuts.com",
                "phone": "+15559902",
                "role": "OWNER"
            }
        ]
        
        owners = []
        for o in owners_data:
            # Check if user exists
            existing = db.query(models.User).filter(models.User.email == o["email"]).first()
            if existing:
                owners.append(existing)
                continue
                
            user = models.User(
                id=str(uuid.uuid4()),
                name=o["name"],
                email=o["email"],
                phone=o["phone"],
                password=get_password_hash("Pass@123"),
                role=o["role"]
            )
            db.add(user)
            owners.append(user)
        
        db.flush() # Get IDs
        
        # 2. Create Shops
        shops_data = [
            {
                "name": "Rivera's Elite Cuts",
                "address": "789 Main St, Downtown",
                "description": "Premium grooming experience in the heart of the city.",
                "ownerId": owners[0].id,
                "phone": owners[0].phone,
                "email": owners[0].email,
                "coordinates": {"lat": 40.7128, "lng": -74.0060},
                "photos": ["https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=800"]
            },
            {
                "name": "The Modern Groom",
                "address": "456 Fashion Ave, Uptown",
                "description": "Contemporary styles and traditional techniques combined.",
                "ownerId": owners[1].id,
                "phone": owners[1].phone,
                "email": owners[1].email,
                "coordinates": {"lat": 40.7306, "lng": -73.9352},
                "photos": ["https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=800"]
            }
        ]
        
        shops = []
        for s in shops_data:
            # Check if shop exists
            existing = db.query(models.Shop).filter(models.Shop.name == s["name"]).first()
            if existing:
                shops.append(existing)
                continue
                
            shop = models.Shop(
                id=str(uuid.uuid4()),
                name=s["name"],
                address=s["address"],
                description=s["description"],
                ownerId=s["ownerId"],
                phone=s["phone"],
                email=s["email"],
                coordinates=s["coordinates"],
                photos=s["photos"]
            )
            db.add(shop)
            shops.append(shop)
            
        db.flush()
        
        # 3. Create Staff (3 for each shop)
        staff_names = [
            ["Carlos M.", "Elena R.", "Julian F."],
            ["Kevin L.", "Maria G.", "Sam W."]
        ]
        
        for i, shop in enumerate(shops):
            for idx, name in enumerate(staff_names[i]):
                email = f"{name.lower().replace(' ', '').replace('.', '')}{i}{idx}@barbersync.com"
                
                # Check if user exists
                existing_user = db.query(models.User).filter(models.User.email == email).first()
                if not existing_user:
                    user = models.User(
                        id=str(uuid.uuid4()),
                        name=name,
                        email=email,
                        phone=f"+155588{i}{idx}",
                        password=get_password_hash("Pass@123"),
                        role="BARBER"
                    )
                    db.add(user)
                    db.flush()
                else:
                    user = existing_user
                
                # Check if staff profile exists
                existing_staff = db.query(models.Staff).filter(models.Staff.userId == user.id).first()
                if not existing_staff:
                    staff_profile = models.Staff(
                        id=str(uuid.uuid4()),
                        userId=user.id,
                        shopId=shop.id,
                        name=name,
                        role="Senior Barber" if idx == 0 else "Barber",
                        experience=3 + idx,
                        description=f"Specialist in modern hair designs and grooming. Expert in clean fades and beard shaping.",
                        imageUrl=f"https://i.pravatar.cc/150?u={user.id}",
                        workPhotos=[
                            "https://images.unsplash.com/photo-1621605815841-2cd7876bad29?w=400",
                            "https://images.unsplash.com/photo-1599351431247-f57933827940?w=400"
                        ]
                    )
                    db.add(staff_profile)
        
        db.commit()
        print("Additional Data seeded successfully!")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
