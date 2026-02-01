import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.database import SessionLocal
from app.database import models

def verify_shop_creation():
    db = SessionLocal()
    try:
        print("\n=== SHOP CREATION VERIFICATION ===\n")
        
        # Summary of all Staff and Users
        all_users = db.query(models.User).all()
        all_staff = db.query(models.Staff).all()
        print(f"\n🔍 Global Stats:")
        print(f"   Total Users in DB: {len(all_users)}")
        print(f"   Total Staff Profiles in DB: {len(all_staff)}")
        
        if len(all_staff) > 0:
            print("\n📜 All Staff Profiles:")
            for s in all_staff:
                print(f"   - Name: {s.name}, UserID: {s.userId}, ShopID: {s.shopId}")

        print("\n========================================")
        
        # Check users
        users = db.query(models.User).filter(models.User.role == 'OWNER').all()
        print(f"📊 Total Owners: {len(users)}")
        for u in users:
            print(f"   - {u.name} ({u.email})")
        
        print()
        
        # Check shops
        shops = db.query(models.Shop).all()
        print(f"🏪 Total Shops: {len(shops)}")
        
        if shops:
            for shop in shops:
                print(f"\n   Shop: {shop.name}")
                print(f"   Owner ID: {shop.ownerId}")
                print(f"   Address: {shop.address}")
                print(f"   Photos: {len(shop.photos or [])} uploaded")
                
                # Count related data
                services = db.query(models.Service).filter(models.Service.shopId == shop.id).all()
                staff = db.query(models.Staff).filter(models.Staff.shopId == shop.id).all()
                
                print(f"   Services: {len(services)}")
                for s in services:
                    print(f"      - {s.name} (${s.price}, {s.duration}min)")
                
                print(f"   Staff: {len(staff)}")
                for st in staff:
                    print(f"      - {st.name} ({st.phone})")
        else:
            print("   ❌ No shops found yet. Register as Owner and create a shop!")
        
        print("\n" + "="*40 + "\n")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_shop_creation()
