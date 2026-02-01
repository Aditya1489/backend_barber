import sys
import os

# Ensure app module can be found
sys.path.append(os.getcwd())

from app.database.database import engine, SessionLocal
from app.database import models

def migrate():
    print("Creating new tables...")
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Migrate Shop Photos
        print("Migrating Shop photos...")
        shops = db.query(models.Shop).all()
        for shop in shops:
            if shop.photos and isinstance(shop.photos, list):
                print(f"  Shop {shop.name}: Found {len(shop.photos)} photos")
                # clear existing rows to avoid dupes if running multiple times? 
                # Better to check if empty first
                if not shop.photo_rows:
                    for i, url in enumerate(shop.photos):
                        if isinstance(url, str):
                            photo = models.ShopPhoto(shopId=shop.id, url=url, order=i)
                            db.add(photo)
        
        # Migrate Staff Data
        print("Migrating Staff data...")
        staff_list = db.query(models.Staff).all()
        for staff in staff_list:
            # Work Photos
            if staff.workPhotos and isinstance(staff.workPhotos, list):
                print(f"  Staff {staff.name}: Found {len(staff.workPhotos)} work photos")
                if not staff.work_photo_rows:
                    for url in staff.workPhotos:
                        if isinstance(url, str):
                            photo = models.StaffWorkPhoto(staffId=staff.id, url=url)
                            db.add(photo)
            
            # Services
            if staff.services and isinstance(staff.services, list):
                print(f"  Staff {staff.name}: Found {len(staff.services)} services")
                # staff.services is a list of Strings (IDs)
                # We need to create StaffService links
                # First check if links exist
                if not staff.service_objs:
                    for service_id in staff.services:
                        if isinstance(service_id, str):
                            # Verify service exists?
                            service = db.query(models.Service).filter(models.Service.id == service_id).first()
                            if service:
                                link = models.StaffService(staffId=staff.id, serviceId=service.id)
                                db.add(link)
                            else:
                                print(f"    Warning: Service {service_id} not found for staff {staff.name}")

        db.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
