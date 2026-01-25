import json
import os
import sys
import uuid
from datetime import datetime

# Add the project root to sys.path to allow importing from app
sys.path.append(os.getcwd())

from app.database.database import engine, SessionLocal, Base
from app.database import models

def parse_date(date_str):
    if not date_str:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except:
        return datetime.utcnow()

def migrate():
    print("Starting migration...")
    
    # 1. Create tables
    print("Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Load JSON data
    db_path = "data/db.json"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return
    
    with open(db_path, "r") as f:
        data = json.load(f)
    
    db = SessionLocal()
    try:
        # 3. Migrate Users
        print(f"Migrating {len(data.get('users', {}))} users...")
        users_map = {} # To keep track of migrated user objects
        for user_id, u in data.get("users", {}).items():
            user = models.User(
                id=u.get("id", user_id),
                name=u.get("name"),
                email=u.get("email"),
                phone=u.get("phone"),
                password=u.get("password", "hashed_default_password"),
                role=u.get("role"),
                profilePhoto=u.get("profilePhoto"),
                permissions=u.get("permissions", {}),
                createdAt=parse_date(u.get("createdAt")),
                experience=u.get("experience"),
                about=u.get("about"),
                portfolio=u.get("portfolio")
            )
            db.add(user)
            users_map[user_id] = user
        
        db.commit()
        print("Users migrated.")

        # 4. Migrate Services (Global pool in JSON)
        # We'll migrate them first, then link them to shops during shop migration
        services_data = data.get("services", {})
        print(f"Loading {len(services_data)} services...")

        # 5. Migrate Shops
        print(f"Migrating {len(data.get('shops', {}))} shops...")
        for shop_id, s in data.get("shops", {}).items():
            shop = models.Shop(
                id=s.get("id", shop_id),
                name=s.get("name"),
                address=s.get("address"),
                description=s.get("description"),
                rating=s.get("rating", 0.0),
                reviewsCount=s.get("reviewsCount", 0),
                photos=s.get("photos", []),
                coordinates=s.get("coordinates", {}),
                ownerId=s.get("ownerId"),
                phone=s.get("phone"),
                email=s.get("email"),
                hours=s.get("hours", {}),
                amenities=s.get("amenities", [])
            )
            db.add(shop)
            db.flush() # Get shop.id if generated

            # Migrate Services for this shop based on serviceRefs
            for service_ref in s.get("serviceRefs", []):
                s_data = services_data.get(service_ref)
                if s_data:
                    service = models.Service(
                        id=s_data.get("id", service_ref),
                        shopId=shop.id,
                        name=s_data.get("name"),
                        price=s_data.get("price"),
                        duration=s_data.get("duration"),
                        imageUrl=s_data.get("imageUrl")
                    )
                    db.add(service)

            # Migrate Staff for this shop based on staffRefs
            for staff_ref in s.get("staffRefs", []):
                staff_info = data.get("staff", {}).get(staff_ref)
                if staff_info:
                    # Find the user ID for this staff if possible. 
                    # In db.json, staff IDs often match user IDs or are linked.
                    # Looking at db.json, st_3fd8adc6 (staff) matches st_3fd8adc6 (user).
                    staff_user_id = staff_info.get("id", staff_ref)
                    
                    staff = models.Staff(
                        id=staff_ref,
                        userId=staff_user_id,
                        shopId=shop.id,
                        name=staff_info.get("name"),
                        role=staff_info.get("role", "Barber"),
                        experience=staff_info.get("experience", 0),
                        rating=staff_info.get("rating", 0.0),
                        reviewsCount=staff_info.get("reviewsCount", 0),
                        imageUrl=staff_info.get("imageUrl"),
                        description=staff_info.get("description"),
                        workPhotos=staff_info.get("workPhotos", [])
                    )
                    db.add(staff)

        db.commit()
        print("Shops, Services, and Staff migrated.")

        # 6. Migrate Bookings
        print(f"Migrating {len(data.get('bookings', {}))} bookings...")
        for b_id, b in data.get("bookings", {}).items():
            booking = models.Booking(
                id=b.get("id", b_id),
                customerId=b.get("userId"),
                shopId=b.get("shopId"),
                staffId=b.get("staffId"),
                services=b.get("services", []),
                date=b.get("date"),
                timeSlot=b.get("timeSlot", ""),
                status=b.get("status", "PENDING"),
                totalAmount=b.get("totalAmount") or b.get("totalPrice", 0.0),
                totalDuration=b.get("totalDuration"),
                bookedAt=parse_date(b.get("bookedAt") or b.get("createdAt")),
                notes=b.get("notes", "")
            )
            db.add(booking)
        
        db.commit()
        print("Bookings migrated.")

        # 7. Migrate Reviews
        print(f"Migrating {len(data.get('reviews', {}))} reviews...")
        for r_id, r in data.get("reviews", {}).items():
            review = models.Review(
                id=r.get("id", r_id),
                shopId=r.get("shopId"),
                customerId=r.get("userId") or r.get("customerId"),
                customerName=r.get("customerName"),
                rating=r.get("rating", 0.0),
                comment=r.get("comment"),
                photos=r.get("photos", []),
                helpful=r.get("helpful", 0),
                createdAt=parse_date(r.get("createdAt"))
            )
            db.add(review)
        
        # 8. Migrate Notifications
        print(f"Migrating {len(data.get('notifications', []))} notifications...")
        for n in data.get("notifications", []):
            notif = models.Notification(
                id=n.get("id", str(uuid.uuid4())),
                userId=n.get("userId"),
                title=n.get("title"),
                body=n.get("body"),
                type=n.get("type", "SYSTEM"),
                data=n.get("data", {}),
                isRead=n.get("isRead", False),
                createdAt=parse_date(n.get("createdAt"))
            )
            db.add(notif)

        db.commit()
        print("Reviews and Notifications migrated.")
        print("Migration completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
