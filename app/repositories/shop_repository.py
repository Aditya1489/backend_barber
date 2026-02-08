"""
Shop repository - handles all shop, service, and staff profile operations.
This is the largest repository due to complex shop hydration logic.
"""
import uuid
from app.repositories.base import BaseRepository
from app.database.database import SessionLocal
from app.database import models


class ShopRepository(BaseRepository):
    """Repository for Shop, Service, and Staff profile operations."""
    
    @classmethod
    def get_hydrated(cls, shop_id: str):
        """Get a shop with all related data (staff, services, photos)."""
        with cls.get_session() as db:
            shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
            if not shop:
                return None
            
            # Base shop data
            hydrated = {c.name: getattr(shop, c.name) for c in shop.__table__.columns}
            
            # Photos
            if shop.photo_rows:
                sorted_photos = sorted(shop.photo_rows, key=lambda x: x.order)
                hydrated["photos"] = [p.url for p in sorted_photos]
            else:
                hydrated["photos"] = []
            
            # Staff
            staff_records = db.query(models.Staff).filter(models.Staff.shopId == shop_id).all()
            hydrated["staff"] = []
            for s in staff_records:
                s_dict = {c.name: getattr(s, c.name) for c in s.__table__.columns}
                s_dict["workPhotos"] = [p.url for p in s.work_photo_rows]
                s_dict["services"] = [svc.id for svc in s.service_objs]
                
                if s.user:
                    s_dict["phone"] = s.user.phone
                    s_dict["email"] = s.user.email
                    s_dict["profilePhoto"] = s.user.profilePhoto
                    if not s.imageUrl:
                        s_dict["imageUrl"] = s.user.profilePhoto
                hydrated["staff"].append(s_dict)
            
            # Services
            services = db.query(models.Service).filter(models.Service.shopId == shop_id).all()
            hydrated["services"] = [
                {c.name: getattr(s, c.name) for c in s.__table__.columns}
                for s in services
            ]
            
            return hydrated
    
    @classmethod
    def get_all_hydrated(cls):
        """Get all shops with full hydration."""
        with cls.get_session() as db:
            shop_ids = [s.id for s in db.query(models.Shop.id).all()]
        return [cls.get_hydrated(sid) for sid in shop_ids]
    
    @classmethod
    def create(cls, shop_data: dict):
        """Create a new shop with services, staff, and photos."""
        db = SessionLocal()
        try:
            # Extract nested data
            services_data = shop_data.pop("services", [])
            staff_data = shop_data.pop("staff", [])
            photos_data = shop_data.pop("photos", [])
            shop_data.pop("serviceRefs", None)
            shop_data.pop("staffRefs", None)
            
            # Create shop
            shop = models.Shop(**shop_data)
            db.add(shop)
            db.flush()
            
            # Add photos
            for i, url in enumerate(photos_data):
                if isinstance(url, str):
                    db.add(models.ShopPhoto(shopId=shop.id, url=url, order=i))
            
            # Add services
            for s in services_data:
                s["shopId"] = shop.id
                db.add(models.Service(**s))
            
            # Add staff
            for st in staff_data:
                phone = st.get("phone")
                email = st.get("email") or f"staff_{uuid.uuid4().hex[:8]}@barbersync.com"
                name = st.get("name", "Unknown Staff")
                
                existing_user = db.query(models.User).filter(
                    (models.User.phone == phone) | (models.User.email == email)
                ).first()
                
                if existing_user:
                    user_id = existing_user.id
                else:
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
                
                existing_profile = db.query(models.Staff).filter(models.Staff.userId == user_id).first()
                if existing_profile:
                    existing_profile.shopId = shop.id
                else:
                    staff_profile = models.Staff(
                        userId=user_id,
                        shopId=shop.id,
                        name=name,
                        role=st.get("role", "Barber"),
                        imageUrl="https://picsum.photos/200/200"
                    )
                    db.add(staff_profile)
                    db.flush()
            
            db.commit()
            return cls.get_hydrated(shop.id)
        except Exception as e:
            db.rollback()
            return None
        finally:
            db.close()
    
    @classmethod
    def update(cls, shop_id: str, update_data: dict):
        """Update a shop."""
        with cls.get_session() as db:
            shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
            if shop:
                # Handle photos
                if "photos" in update_data:
                    new_photos = update_data.pop("photos")
                    if isinstance(new_photos, list):
                        db.query(models.ShopPhoto).filter(models.ShopPhoto.shopId == shop_id).delete()
                        for i, url in enumerate(new_photos):
                            if isinstance(url, str):
                                db.add(models.ShopPhoto(shopId=shop_id, url=url, order=i))
                
                for key, value in update_data.items():
                    if hasattr(shop, key):
                        setattr(shop, key, value)
                db.commit()
                return cls.get_hydrated(shop_id)
            return None
    
    @classmethod
    def delete(cls, shop_id: str):
        """Delete a shop."""
        with cls.get_session() as db:
            shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
            if shop:
                db.delete(shop)
                db.commit()
                return True
            return False
    
    @classmethod
    def add_photo(cls, shop_id: str, photo_url: str):
        """Add a photo to a shop."""
        with cls.get_session() as db:
            shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
            if shop:
                count = db.query(models.ShopPhoto).filter(models.ShopPhoto.shopId == shop_id).count()
                new_photo = models.ShopPhoto(shopId=shop_id, url=photo_url, order=count)
                db.add(new_photo)
                db.commit()
                
                photos = db.query(models.ShopPhoto).filter(
                    models.ShopPhoto.shopId == shop_id
                ).order_by(models.ShopPhoto.order).all()
                return [p.url for p in photos]
            return None


class ServiceRepository(BaseRepository):
    """Repository for Service operations."""
    
    @classmethod
    def create(cls, service_data: dict):
        """Create a new service."""
        with cls.get_session() as db:
            service = models.Service(**service_data)
            db.add(service)
            db.commit()
            db.refresh(service)
            return {c.name: getattr(service, c.name) for c in service.__table__.columns}
    
    @classmethod
    def update(cls, service_id: str, update_data: dict):
        """Update a service."""
        with cls.get_session() as db:
            service = db.query(models.Service).filter(models.Service.id == service_id).first()
            if service:
                for key, value in update_data.items():
                    if hasattr(service, key):
                        setattr(service, key, value)
                db.commit()
                db.refresh(service)
                return {c.name: getattr(service, c.name) for c in service.__table__.columns}
            return None
    
    @classmethod
    def delete(cls, service_id: str):
        """Delete a service."""
        with cls.get_session() as db:
            service = db.query(models.Service).filter(models.Service.id == service_id).first()
            if service:
                db.delete(service)
                db.commit()
                return True
            return False


class StaffProfileRepository(BaseRepository):
    """Repository for Staff profile operations."""
    
    @classmethod
    def get_full_profile(cls, staff_id: str):
        """Get full staff profile with shop info."""
        with cls.get_session() as db:
            staff = db.query(models.Staff).filter(
                (models.Staff.id == staff_id) | (models.Staff.userId == staff_id)
            ).first()
            
            if not staff:
                user = db.query(models.User).filter(models.User.id == staff_id).first()
                if not user:
                    return None
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
            shop = ShopRepository.get_hydrated(staff.shopId) if staff.shopId else None
            
            return {
                "id": staff.id,
                "userId": staff.userId,
                "name": staff.name or user.name,
                "photo": user.profilePhoto,
                "imageUrl": staff.imageUrl or user.profilePhoto,
                "role": staff.role or user.role,
                "experience": staff.experience if staff.experience is not None else getattr(user, "experience", 0),
                "description": staff.description if staff.description is not None else getattr(user, "about", ""),
                "workPhotos": [p.url for p in staff.work_photo_rows],
                "rating": staff.rating,
                "reviewsCount": staff.reviewsCount,
                "services": [s.id for s in staff.service_objs] if staff.service_objs else [],
                "skills": staff.skills or "",
                "workingDays": staff.workingDays,
                "workingHours": staff.workingHours,
                "bufferTime": staff.bufferTime,
                "isAvailable": staff.isAvailable,
                "shop": shop
            }
    
    @classmethod
    def update(cls, staff_id: str, update_data: dict):
        """Update a staff profile."""
        with cls.get_session() as db:
            staff = db.query(models.Staff).filter(
                (models.Staff.id == staff_id) | (models.Staff.userId == staff_id)
            ).first()
            
            if staff:
                # Handle field mapping from User to StaffProfile
                if "about" in update_data:
                    update_data["description"] = update_data.pop("about")
                
                # Check for experience directly or via User
                if "experience" in update_data:
                    staff.experience = update_data.pop("experience")

                # Handle portfolio sync for existing staff
                portfolio = update_data.pop("portfolio", None) or update_data.pop("workPhotos", None)
                if portfolio is not None and isinstance(portfolio, list):
                    db.query(models.StaffWorkPhoto).filter(
                        models.StaffWorkPhoto.staffId == staff.id
                    ).delete()
                    for url in portfolio:
                        db.add(models.StaffWorkPhoto(staffId=staff.id, url=url))

                for key, value in update_data.items():
                    if hasattr(staff, key):
                        setattr(staff, key, value)
                db.commit()
                db.refresh(staff)
                return {c.name: getattr(staff, c.name) for c in staff.__table__.columns}
            else:
                # Create new staff profile if not exists
                user = db.query(models.User).filter(models.User.id == staff_id).first()
                if not user:
                    return None
                
                new_staff = models.Staff(
                    userId=user.id,
                    name=user.name,
                    experience=update_data.get("experience", 0),
                    description=update_data.get("about") or update_data.get("description", ""),
                    imageUrl=update_data.get("imageUrl") or update_data.get("profilePhoto") or user.profilePhoto,
                    role=update_data.get("role", "Barber"),
                    workingDays=update_data.get("workingDays", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]),
                    workingHours=update_data.get("workingHours", {}),
                    bufferTime=update_data.get("bufferTime", 0),
                    isAvailable=update_data.get("isAvailable", True)
                )
                db.add(new_staff)
                db.commit()
                db.refresh(new_staff)
                staff = new_staff
                
                # Handle nested data for new profile
                if "workPhotos" in update_data:
                    for url in update_data["workPhotos"]:
                        db.add(models.StaffWorkPhoto(staffId=staff.id, url=url))
                elif "portfolio" in update_data:
                    for url in update_data["portfolio"]:
                        db.add(models.StaffWorkPhoto(staffId=staff.id, url=url))
                
                db.commit()
                db.refresh(staff)
                
                res = {c.name: getattr(staff, c.name) for c in staff.__table__.columns}
                res["workPhotos"] = [p.url for p in staff.work_photo_rows]
                res["services"] = [s.id for s in staff.service_objs]
                return res
            return None


# Backward-compatible function exports
def get_hydrated_shop(shop_id: str):
    """Get hydrated shop. (Backward compatible)"""
    return ShopRepository.get_hydrated(shop_id)


def get_all_hydrated_shops():
    """Get all hydrated shops. (Backward compatible)"""
    return ShopRepository.get_all_hydrated()


def create_shop(shop_data: dict):
    """Create a shop. (Backward compatible)"""
    return ShopRepository.create(shop_data)


def update_shop(shop_id: str, update_data: dict):
    """Update a shop. (Backward compatible)"""
    return ShopRepository.update(shop_id, update_data)


def delete_shop(shop_id: str):
    """Delete a shop. (Backward compatible)"""
    return ShopRepository.delete(shop_id)


def add_shop_photo(shop_id: str, photo_url: str):
    """Add shop photo. (Backward compatible)"""
    return ShopRepository.add_photo(shop_id, photo_url)


def add_service(service_data: dict):
    """Add service. (Backward compatible)"""
    return ServiceRepository.create(service_data)


def update_service(service_id: str, update_data: dict):
    """Update service. (Backward compatible)"""
    return ServiceRepository.update(service_id, update_data)


def delete_service(service_id: str):
    """Delete service. (Backward compatible)"""
    return ServiceRepository.delete(service_id)


def get_staff_full_profile(staff_id: str):
    """Get staff profile. (Backward compatible)"""
    return StaffProfileRepository.get_full_profile(staff_id)


def update_staff_profile(staff_id: str, update_data: dict):
    """Update staff profile. (Backward compatible)"""
    return StaffProfileRepository.update(staff_id, update_data)
