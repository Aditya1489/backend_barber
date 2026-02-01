from app.database.database import SessionLocal
from app.database import models
import json

def fix_paths():
    db = SessionLocal()
    try:
        print("Starting DB Cleanup...")
        
        # 1. Fix Shops
        shops = db.query(models.Shop).all()
        for s in shops:
            if s.photos:
                original_len = len(s.photos)
                # Keep only valid URLs (http) or server relative paths (/uploads)
                # Reject absolute local paths (/data, /Users)
                new_photos = [p for p in s.photos if p.startswith('http') or (p.startswith('/') and not p.startswith('/data') and not p.startswith('/Users'))]
                
                if len(new_photos) != original_len:
                    print(f"Shop {s.name}: Removed {original_len - len(new_photos)} bad photos.")
                    s.photos = new_photos

        # 2. Fix Users (Profile Photo & Portfolio)
        users = db.query(models.User).all()
        for u in users:
            # Profile Photo
            if u.profilePhoto and (u.profilePhoto.startswith('/data') or u.profilePhoto.startswith('/Users')):
                print(f"User {u.name}: Removed bad profile photo {u.profilePhoto}")
                u.profilePhoto = None
            
            # Portfolio
            if u.portfolio:
                original_len = len(u.portfolio)
                new_portfolio = [p for p in u.portfolio if p.startswith('http') or (p.startswith('/') and not p.startswith('/data') and not p.startswith('/Users'))]
                if len(new_portfolio) != original_len:
                     print(f"User {u.name}: Removed {original_len - len(new_portfolio)} bad portfolio photos.")
                     u.portfolio = new_portfolio
        
        # 3. Fix Staff (WorkPhotos, ImageUrl)
        staff_list = db.query(models.Staff).all()
        for st in staff_list:
             if st.imageUrl and (st.imageUrl.startswith('/data') or st.imageUrl.startswith('/Users')):
                print(f"Staff {st.name}: Removed bad image url {st.imageUrl}")
                st.imageUrl = None
             
             if st.workPhotos:
                original_len = len(st.workPhotos)
                new_work = [p for p in st.workPhotos if p.startswith('http') or (p.startswith('/') and not p.startswith('/data') and not p.startswith('/Users'))]
                if len(new_work) != original_len:
                     print(f"Staff {st.name}: Removed {original_len - len(new_work)} bad work photos.")
                     st.workPhotos = new_work

        db.commit()
        print("DB Cleanup Complete!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_paths()
