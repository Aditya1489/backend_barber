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
        
        # Hydrate manually for now to match old JSON structure
        hydrated = {c.name: getattr(shop, c.name) for c in shop.__table__.columns}
        
        # Get staff linked to this shop
        staff = db.query(models.Staff).filter(models.Staff.shopId == shop_id).all()
        hydrated["staff"] = [
            {c.name: getattr(s, c.name) for c in s.__table__.columns}
            for s in staff
        ]
        
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
        # Separate related data
        services_data = shop_data.pop("services", [])
        staff_data = shop_data.pop("staff", [])
        
        # We don't use serviceRefs/staffRefs in SQL, but we might receive them
        shop_data.pop("serviceRefs", None)
        shop_data.pop("staffRefs", None)

        shop = models.Shop(**shop_data)
        db.add(shop)
        db.flush()
        
        # Add services
        for s in services_data:
            s["shopId"] = shop.id
            db.add(models.Service(**s))
            
        # Add staff
        for st in staff_data:
            st["shopId"] = shop.id
            db.add(models.Staff(**st))
            
        db.commit()
        return get_hydrated_shop(shop.id)
    finally:
        db.close()

def update_shop(shop_id: str, update_data: dict):
    db = get_db_session()
    try:
        shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
        if shop:
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
        staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
        if staff:
            for key, value in update_data.items():
                if hasattr(staff, key):
                    setattr(staff, key, value)
            db.commit()
            db.refresh(staff)
            return {c.name: getattr(staff, c.name) for c in staff.__table__.columns}
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
            "experience": staff.experience or getattr(user, "experience", 0),
            "description": staff.description or getattr(user, "about", ""),
            "workPhotos": staff.workPhotos or getattr(user, "portfolio", []),
            "rating": staff.rating,
            "reviewsCount": staff.reviewsCount,
            "shop": shop
        }
    finally:
        db.close()

def add_shop_photo(shop_id: str, photo_url: str):
    db = get_db_session()
    try:
        shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
        if shop:
            photos = list(shop.photos or [])
            photos.append(photo_url)
            shop.photos = photos
            db.commit()
            return photos
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

def get_bookings(customer_id=None, staff_id=None, shop_id=None, status=None):
    db = get_db_session()
    try:
        query = db.query(models.Booking)
        if customer_id: query = query.filter(models.Booking.customerId == customer_id)
        if staff_id: query = query.filter(models.Booking.staffId == staff_id)
        if shop_id: query = query.filter(models.Booking.shopId == shop_id)
        if status: query = query.filter(models.Booking.status == status)
        
        bookings = query.all()
        return [{c.name: getattr(b, c.name) for c in b.__table__.columns} for b in bookings]
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
            customerId=review_data["customerId"],
            customerName=review_data["customerName"],
            rating=review_data["rating"],
            comment=review_data["comment"],
            photos=review_data.get("photos", []),
            helpful=0
        )
        db.add(new_review)
        db.commit()
        db.refresh(new_review)
        return {
            "id": new_review.id,
            "shopId": new_review.shopId,
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

def get_reviews(shop_id=None, customer_id=None):
    db = SessionLocal()
    try:
        query = db.query(models.Review)
        if shop_id:
            query = query.filter(models.Review.shopId == shop_id)
        if customer_id:
            query = query.filter(models.Review.customerId == customer_id)
        
        reviews = query.order_by(models.Review.createdAt.desc()).all()
        return [{
            "id": r.id,
            "shopId": r.shopId,
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
