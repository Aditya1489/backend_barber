import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.database import SessionLocal, engine
from app.database import models

# Helper to get a DB session for these utility functions
def get_db_session():
    return SessionLocal()

def get_user_by_email(email: str):
    db = get_db_session()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user: return None
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}
    finally:
        db.close()

def get_user_by_id(user_id: str):
    db = get_db_session()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user: return None
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}
    finally:
        db.close()

def get_user_by_phone(phone: str):
    db = get_db_session()
    try:
        # Check for both exact match and normalized match if needed
        # For simplicity, we'll start with exact match as the migration kept it that way
        user = db.query(models.User).filter(models.User.phone == phone).first()
        if not user: return None
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}
    finally:
        db.close()

def add_user(user_data):
    db = get_db_session()
    try:
        # Check if user already exists in dict-like data
        user = models.User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {c.name: getattr(user, c.name) for c in user.__table__.columns}
    finally:
        db.close()

def update_user(user_id: str, update_data: dict):
    db = get_db_session()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.commit()
            db.refresh(user)
            return {c.name: getattr(user, c.name) for c in user.__table__.columns}
        return None
    finally:
        db.close()

def get_hydrated_shop(shop_id: str):
    db = get_db_session()
    try:
        shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
        if not shop:
            return None
        
        # Hydrate manually
        hydrated = {c.name: getattr(shop, c.name) for c in shop.__table__.columns}
        
        # Override photos from new table
        # shop.photo_rows might be lazy loaded, but we are in a session.
        # sort by order
        if shop.photo_rows:
            sorted_photos = sorted(shop.photo_rows, key=lambda x: x.order)
            hydrated["photos"] = [p.url for p in sorted_photos]
        else:
            # Fallback (though we migrated) or empty
            hydrated["photos"] = []

        # Get staff linked to this shop
        staff_records = db.query(models.Staff).filter(models.Staff.shopId == shop_id).all()
        hydrated["staff"] = []
        for s in staff_records:
            s_dict = {c.name: getattr(s, c.name) for c in s.__table__.columns}
            # Hydrate relations
            s_dict["workPhotos"] = [p.url for p in s.work_photo_rows]
            s_dict["services"] = [svc.id for svc in s.service_objs]
            
            # Include basic user info
            if s.user:
                s_dict["phone"] = s.user.phone
                s_dict["email"] = s.user.email
                s_dict["profilePhoto"] = s.user.profilePhoto
                # Fallback for imageUrl if not set in staff record
                if not s.imageUrl:
                    s_dict["imageUrl"] = s.user.profilePhoto
            hydrated["staff"].append(s_dict)
        
        # Get services linked to this shop
        services = db.query(models.Service).filter(models.Service.shopId == shop_id).all()
        hydrated["services"] = [
            {c.name: getattr(s, c.name) for c in s.__table__.columns}
            for s in services
        ]
        
        return hydrated
    finally:
        db.close()

def get_all_hydrated_shops():
    db = get_db_session()
    try:
        shop_ids = [s.id for s in db.query(models.Shop.id).all()]
        return [get_hydrated_shop(sid) for sid in shop_ids]
    finally:
        db.close()

def create_shop(shop_data: dict):
    db = get_db_session()
    try:
        print(f"[CREATE_SHOP] Starting shop creation for owner: {shop_data.get('ownerId')}")
        
        # 1. Extract and Clean Data
        services_data = shop_data.pop("services", [])
        staff_data = shop_data.pop("staff", [])
        photos_data = shop_data.pop("photos", []) # Pop photos to avoid saving to JSON column
        
        print(f"[CREATE_SHOP] Raw services data: {len(services_data)} items")
        print(f"[CREATE_SHOP] Raw staff data: {staff_data}")
        
        # Remove any non-model internal refs
        shop_data.pop("serviceRefs", None)
        shop_data.pop("staffRefs", None)

        # 2. Create the Shop
        shop = models.Shop(**shop_data)
        db.add(shop)
        db.flush()
        print(f"[CREATE_SHOP] Shop record created: {shop.id}")
        
        # 3. Add Photos (New Table)
        for i, url in enumerate(photos_data):
            if isinstance(url, str):
                db.add(models.ShopPhoto(shopId=shop.id, url=url, order=i))
        print(f"[CREATE_SHOP] Attached {len(photos_data)} photos")

        # 4. Add Services
        for s in services_data:
            s["shopId"] = shop.id
            db.add(models.Service(**s))
        print(f"[CREATE_SHOP] Attached {len(services_data)} services")
            
        # 4. Add Staff (The Tricky Part)
        print(f"[CREATE_SHOP] Entering staff loop for {len(staff_data)} staff members")
        for i, st in enumerate(staff_data):
            print(f"[CREATE_SHOP] Processing staff {i}: {st}")
            phone = st.get("phone")
            email = st.get("email") or f"staff_{uuid.uuid4().hex[:8]}@barbersync.com"
            name = st.get("name", "Unknown Staff")

            # Check if User already exists
            existing_user = db.query(models.User).filter(
                (models.User.phone == phone) | (models.User.email == email)
            ).first()

            if existing_user:
                user_id = existing_user.id
                print(f"[CREATE_SHOP]   -> Using existing user ID: {user_id}")
            else:
                # Create New User
                new_user = models.User(
                    name=name,
                    phone=phone,
                    email=email,
                    role="BARBER",
                    password="hashed_default_password",
                    permissions={"location": True, "notifications": True}
                )
                db.add(new_user)
                db.flush()
                user_id = new_user.id
                print(f"[CREATE_SHOP]   -> Created new user ID: {user_id}")
            
            # Check if Staff profile already exists for this user
            existing_profile = db.query(models.Staff).filter(models.Staff.userId == user_id).first()
            if existing_profile:
                existing_profile.shopId = shop.id
                print(f"[CREATE_SHOP]   -> Linked existing profile to shop")
            else:
                # Create New Staff Profile (STRICT FILTERING)
                staff_profile = models.Staff(
                    userId=user_id,
                    shopId=shop.id,
                    name=name,
                    role=st.get("role", "Barber"),
                    imageUrl="https://picsum.photos/200/200"
                )
                db.add(staff_profile)
                db.flush() # Flush to catch any database errors for this record
                print(f"[CREATE_SHOP]   -> Created new staff profile")
            
        db.commit()
        print(f"[CREATE_SHOP] ✅ Transaction Committed: Shop {shop.id} is live.")
        return get_hydrated_shop(shop.id)
    except Exception as e:
        print(f"[CREATE_SHOP] ❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None
    finally:
        db.close()

def update_shop(shop_id: str, update_data: dict):
    db = get_db_session()
    try:
        shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
        if shop:
            # Handle Photos Separately
            if "photos" in update_data:
                new_photos = update_data.pop("photos")
                if isinstance(new_photos, list):
                    # Delete existing photos
                    db.query(models.ShopPhoto).filter(models.ShopPhoto.shopId == shop_id).delete()
                    # Add new photos
                    for i, url in enumerate(new_photos):
                        if isinstance(url, str):
                            db.add(models.ShopPhoto(shopId=shop_id, url=url, order=i))

            for key, value in update_data.items():
                if hasattr(shop, key):
                    setattr(shop, key, value)
            db.commit()
            return get_hydrated_shop(shop_id)
        return None
    finally:
        db.close()

def add_service(service_data: dict):
    db = get_db_session()
    try:
        service = models.Service(**service_data)
        db.add(service)
        db.commit()
        db.refresh(service)
        return {c.name: getattr(service, c.name) for c in service.__table__.columns}
    finally:
        db.close()

def update_staff_profile(staff_id: str, update_data: dict):
    db = get_db_session()
    try:
        # Try lookup by primary ID first, then by userId
        staff = db.query(models.Staff).filter(
            (models.Staff.id == staff_id) | (models.Staff.userId == staff_id)
        ).first()
        if staff:
            # Handle Work Photos
            if "workPhotos" in update_data:
                photos = update_data.pop("workPhotos")
                if isinstance(photos, list):
                    db.query(models.StaffWorkPhoto).filter(models.StaffWorkPhoto.staffId == staff.id).delete()
                    for url in photos:
                        if isinstance(url, str):
                            db.add(models.StaffWorkPhoto(staffId=staff.id, url=url))

            # Handle Services
            if "services" in update_data:
                service_ids = update_data.pop("services")
                if isinstance(service_ids, list):
                     db.query(models.StaffService).filter(models.StaffService.staffId == staff.id).delete()
                     for sid in service_ids:
                         if isinstance(sid, str):
                             db.add(models.StaffService(staffId=staff.id, serviceId=sid))

            for key, value in update_data.items():
                if hasattr(staff, key):
                    setattr(staff, key, value)
            db.commit()
            db.refresh(staff)
        else:
            # If staff not found, we assume the provided staff_id is a userId
            # and we should create a profile for them.
            user = db.query(models.User).filter(models.User.id == staff_id).first()
            if not user:
                return None
            
            # Extract basic professional info from update_data or fall back
            new_staff = models.Staff(
                userId=user.id,
                name=user.name,
                experience=update_data.get("experience", 0),
                description=update_data.get("description", ""),
                imageUrl=update_data.get("imageUrl") or user.profilePhoto,
                role=update_data.get("role", "Barber")
            )
            db.add(new_staff)
            db.commit()
            db.refresh(new_staff)
            staff = new_staff
            
            # Return dict manual composition
            # (Fetching fresh to include relations)
            # Or just update the returned dict manually
            
            # Just let the caller re-fetch or return what we have
            # But get_staff_full_profile logic should be reused if possible.
            # For now, return simple dict but with updated lists
            res = {c.name: getattr(staff, c.name) for c in staff.__table__.columns}
            res["workPhotos"] = [p.url for p in staff.work_photo_rows]
            res["services"] = [s.id for s in staff.service_objs]
            return res
        return None
    finally:
        db.close()

def delete_shop(shop_id: str):
    db = get_db_session()
    try:
        shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
        if shop:
            db.delete(shop)
            db.commit()
            return True
        return False
    finally:
        db.close()

def delete_service(service_id: str):
    db = get_db_session()
    try:
        service = db.query(models.Service).filter(models.Service.id == service_id).first()
        if service:
            db.delete(service)
            db.commit()
            return True
        return False
    finally:
        db.close()

def update_service(service_id: str, update_data: dict):
    db = get_db_session()
    try:
        service = db.query(models.Service).filter(models.Service.id == service_id).first()
        if service:
            for key, value in update_data.items():
                if hasattr(service, key):
                    setattr(service, key, value)
            db.commit()
            db.refresh(service)
            return {c.name: getattr(service, c.name) for c in service.__table__.columns}
        return None
    finally:
        db.close()

def get_staff_full_profile(staff_id: str):
    db = get_db_session()
    try:
        # Try finding by staff profile ID or user ID
        staff = db.query(models.Staff).filter(
            (models.Staff.id == staff_id) | (models.Staff.userId == staff_id)
        ).first()
        
        if not staff:
            # Fallback for search by phone if it was a user ID previously
            user = db.query(models.User).filter(models.User.id == staff_id).first()
            if not user: return None
            return {
                "id": user.id,
                "name": user.name,
                "photo": user.profilePhoto,
                "role": user.role,
                "experience": getattr(user, "experience", 0),
                "description": getattr(user, "about", ""),
                "workPhotos": getattr(user, "portfolio", []),
                "shop": None
            }
        
        user = staff.user
        shop = get_hydrated_shop(staff.shopId) if staff.shopId else None
        
        return {
            "id": staff.id,
            "userId": staff.userId,
            "name": staff.name or user.name,
            "photo": user.profilePhoto,
            "imageUrl": staff.imageUrl or user.profilePhoto,
            "role": staff.role or user.role,
            "experience": staff.experience if staff.experience is not None else getattr(user, "experience", 0),
            "description": staff.description if staff.description is not None else getattr(user, "about", ""),
            "workPhotos": [p.url for p in staff.work_photo_rows],  # No fallback - return empty list if none
            "rating": staff.rating,
            "reviewsCount": staff.reviewsCount,
            "services": [s.id for s in staff.service_objs] if staff.service_objs else [],
            "skills": staff.skills or "",  # Return empty string if no skills
            "shop": shop
        }
    finally:
        db.close()

def add_shop_photo(shop_id: str, photo_url: str):
    db = get_db_session()
    try:
        shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
        if shop:
            # Calculate next order index
            count = db.query(models.ShopPhoto).filter(models.ShopPhoto.shopId == shop_id).count()
            
            new_photo = models.ShopPhoto(shopId=shop_id, url=photo_url, order=count)
            db.add(new_photo)
            db.commit()
            
            # Return updated list
            # We fetch all (including the new one) ordered by 'order'
            photos = db.query(models.ShopPhoto).filter(models.ShopPhoto.shopId == shop_id).order_by(models.ShopPhoto.order).all()
            return [p.url for p in photos]
        return None
    finally:
        db.close()

def create_booking(booking_data: dict):
    db = get_db_session()
    try:
        booking = models.Booking(**booking_data)
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return {c.name: getattr(booking, c.name) for c in booking.__table__.columns}
    finally:
        db.close()

def get_bookings(customer_id=None, staff_id=None, shop_id=None, status=None, limit=None):
    db = get_db_session()
    try:
        query = db.query(models.Booking, models.User).join(models.User, models.Booking.customerId == models.User.id)
        if customer_id: query = query.filter(models.Booking.customerId == customer_id)
        if staff_id: query = query.filter(models.Booking.staffId == staff_id)
        if shop_id: query = query.filter(models.Booking.shopId == shop_id)
        if status: query = query.filter(models.Booking.status == status)
        
        # Sort by date and time (newest first) to make the limit meaningful
        query = query.order_by(models.Booking.date.desc(), models.Booking.timeSlot.desc())
        
        if limit:
            query = query.limit(limit)
        
        results = query.all()
        bookings_with_customers = []
        for booking, user in results:
            b_dict = {c.name: getattr(booking, c.name) for c in booking.__table__.columns}
            b_dict["customerName"] = user.name
            b_dict["customerPhoto"] = user.profilePhoto
            bookings_with_customers.append(b_dict)
            
        return bookings_with_customers
    finally:
        db.close()

def get_booking_by_id(booking_id: str):
    db = get_db_session()
    try:
        booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
        return {c.name: getattr(booking, c.name) for c in booking.__table__.columns} if booking else None
    finally:
        db.close()

def update_booking(booking_id: str, update_data: dict):
    db = get_db_session()
    try:
        booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
        if booking:
            for key, value in update_data.items():
                if hasattr(booking, key):
                    setattr(booking, key, value)
            db.commit()
            db.refresh(booking)
            return {c.name: getattr(booking, c.name) for c in booking.__table__.columns}
        return None
    finally:
        db.close()


def create_review(review_data: dict):
    db = SessionLocal()
    try:
        new_review = models.Review(
            id=str(uuid.uuid4()),
            shopId=review_data["shopId"],
            staffId=review_data.get("staffId"),  # NEW: Optional staff link
            customerId=review_data["customerId"],
            customerName=review_data["customerName"],
            rating=review_data["rating"],
            comment=review_data.get("comment", ""),
            photos=review_data.get("photos", []),
            helpful=0
        )
        db.add(new_review)
        db.flush()  # Flush to get the review in DB before aggregation
        
        # --- RATING AGGREGATION ---
        try:
            shop_id = review_data["shopId"]
            staff_id = review_data.get("staffId")
            
            print(f"DEBUG: Starting aggregation for shop {shop_id} and staff {staff_id}")
            
            # 1. Update Shop rating/reviewsCount
            shop_reviews = db.query(models.Review).filter(models.Review.shopId == shop_id).all()
            if shop_reviews:
                shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
                if shop:
                    avg_rating = sum(r.rating for r in shop_reviews) / len(shop_reviews)
                    shop.rating = round(avg_rating, 1)
                    shop.reviewsCount = len(shop_reviews)
                    print(f"DEBUG: Shop {shop_id} rating updated to {shop.rating} ({shop.reviewsCount} reviews)")
            
            # 2. Update Staff rating/reviewsCount (if staffId provided)
            if staff_id:
                # Ensure staff_id is a string for the query if it's coming from a raw review_data
                staff_id_str = str(staff_id)
                staff_reviews = db.query(models.Review).filter(models.Review.staffId == staff_id_str).all()
                print(f"DEBUG: Found {len(staff_reviews)} reviews for staff {staff_id_str}")
                
                if staff_reviews:
                    staff = db.query(models.Staff).filter(models.Staff.id == staff_id_str).first()
                    if staff:
                        avg_rating = sum(r.rating for r in staff_reviews) / len(staff_reviews)
                        staff.rating = round(avg_rating, 1)
                        staff.reviewsCount = len(staff_reviews)
                        print(f"DEBUG: Staff {staff_id_str} rating updated to {staff.rating} ({staff.reviewsCount} reviews)")
                    else:
                        print(f"DEBUG: Staff profile {staff_id_str} not found in staff_profiles table")
        except Exception as agg_err:
            print(f"ERROR: Aggregation failed: {agg_err}")
            # We don't raise here to ensure the review creation itself succeeds
            
        db.commit()
        db.refresh(new_review)
        
        return {
            "id": new_review.id,
            "shopId": new_review.shopId,
            "staffId": str(new_review.staffId) if new_review.staffId else None,
            "customerId": new_review.customerId,
            "customerName": new_review.customerName,
            "rating": new_review.rating,
            "comment": new_review.comment,
            "photos": new_review.photos,
            "createdAt": new_review.createdAt.isoformat() + "Z",
            "helpful": new_review.helpful
        }
    finally:
        db.close()

def get_reviews(shop_id=None, customer_id=None, staff_id=None):
    db = SessionLocal()
    try:
        query = db.query(models.Review)
        if shop_id:
            query = query.filter(models.Review.shopId == shop_id)
        if customer_id:
            query = query.filter(models.Review.customerId == customer_id)
        if staff_id:
            query = query.filter(models.Review.staffId == staff_id)
        
        reviews = query.order_by(models.Review.createdAt.desc()).all()
        return [{
            "id": r.id,
            "shopId": r.shopId,
            "staffId": str(r.staffId) if r.staffId else None,
            "customerId": r.customerId,
            "customerName": r.customerName,
            "rating": r.rating,
            "comment": r.comment,
            "photos": r.photos,
            "createdAt": r.createdAt.isoformat() + "Z",
            "helpful": r.helpful
        } for r in reviews]
    finally:
        db.close()

def update_review(review_id: str, update_data: dict):
    db = SessionLocal()
    try:
        review = db.query(models.Review).filter(models.Review.id == review_id).first()
        if not review:
            return None
        
        for key, value in update_data.items():
            if hasattr(review, key):
                setattr(review, key, value)
        
        db.commit()
        db.refresh(review)
        return {
            "id": review.id,
            "shopId": review.shopId,
            "customerId": review.customerId,
            "customerName": review.customerName,
            "rating": review.rating,
            "comment": review.comment,
            "photos": review.photos,
            "createdAt": review.createdAt.isoformat() + "Z",
            "helpful": review.helpful
        }
    finally:
        db.close()

def delete_review(review_id: str):
    db = SessionLocal()
    try:
        review = db.query(models.Review).filter(models.Review.id == review_id).first()
        if not review:
            return False
        db.delete(review)
        db.commit()
        return True
    finally:
        db.close()

def create_notification(data: dict):
    db = SessionLocal()
    try:
        new_notif = models.Notification(
            id=str(uuid.uuid4()),
            userId=data["userId"],
            title=data["title"],
            body=data["body"],
            type=data["type"],
            data=data.get("data", {}),
            isRead=False
        )
        db.add(new_notif)
        db.commit()
        db.refresh(new_notif)
        return {
            "id": new_notif.id,
            "userId": new_notif.userId,
            "title": new_notif.title,
            "body": new_notif.body,
            "isRead": new_notif.isRead,
            "createdAt": new_notif.createdAt.isoformat() + "Z"
        }
    finally:
        db.close()

def get_notifications(user_id: str):
    db = SessionLocal()
    try:
        notifs = db.query(models.Notification).filter(models.Notification.userId == user_id).order_by(models.Notification.createdAt.desc()).all()
        return [{
            "id": n.id,
            "userId": n.userId,
            "title": n.title,
            "body": n.body,
            "type": n.type,
            "data": n.data,
            "isRead": n.isRead,
            "createdAt": n.createdAt.isoformat() + "Z"
        } for n in notifs]
    finally:
        db.close()

def mark_notification_read(notif_id: str):
    db = SessionLocal()
    try:
        notif = db.query(models.Notification).filter(models.Notification.id == notif_id).first()
        if notif:
            notif.isRead = True
            db.commit()
            return True
        return False
    finally:
        db.close()

# Legacy placeholders removed. Backend now fully PostgreSQL powered.
