from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
import uuid
import math

router = APIRouter(prefix="/shops", tags=["shops"])

from app.db import (
    get_hydrated_shop, 
    get_all_hydrated_shops, 
    create_shop, 
    update_shop, 
    delete_shop,
    add_service, 
    update_service, 
    delete_service,
    update_staff_profile, 
    get_staff_full_profile,
    add_shop_photo,
    get_user_by_phone,
    add_user
)

# Request/Response Models
class CreateShopRequest(BaseModel):
    name: str
    address: str
    description: str
    coordinates: dict
    ownerId: str
    phone: str
    email: str
    photos: Optional[List[str]] = []
    hours: Optional[dict] = {}
    amenities: Optional[List[str]] = []
    services: Optional[List[dict]] = []
    staff: Optional[List[dict]] = []

class AddServiceRequest(BaseModel):
    name: str
    price: float
    duration: int
    imageUrl: Optional[str] = None

class AddPhotoRequest(BaseModel):
    photoUrl: str

class UpdateServiceRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    duration: Optional[int] = None
    imageUrl: Optional[str] = None

class CreateStaffRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None

class UpdateShopRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    photos: Optional[List[str]] = None
    hours: Optional[dict] = None
    amenities: Optional[List[str]] = None
    coordinates: Optional[dict] = None

class UpdateStaffProfileRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    experience: Optional[int] = None
    description: Optional[str] = None
    workPhotos: Optional[List[str]] = None
    profilePhoto: Optional[str] = None
    portfolio: Optional[List[str]] = None
    services: Optional[List[str]] = None  # List of service IDs
    skills: Optional[str] = None  # Comma-separated skill names
    workingDays: Optional[List[str]] = None
    workingHours: Optional[dict] = None
    bufferTime: Optional[int] = None
    isAvailable: Optional[bool] = None

# Routes
@router.get("/", response_model=List[dict])
async def get_shops(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius: Optional[float] = Query(10.0),  # km
    search: Optional[str] = Query(None)
):
    """Get all shops with optional location and search filters"""
    
    shops = get_all_hydrated_shops()
    
    # Apply location-based filtering
    if lat is not None and lng is not None:
        def calculate_distance(s_lat, s_lng):
            # Simple Haversine approximation
            R = 6371  # Earth radius in km
            d_lat = math.radians(s_lat - lat)
            d_lng = math.radians(s_lng - lng)
            a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(s_lat)) * math.sin(d_lng/2)**2
            c = 2 * math.asin(math.sqrt(a))
            return R * c

        shops = [
            s for s in shops
            if calculate_distance(s["coordinates"]["lat"], s["coordinates"]["lng"]) <= radius
        ]

    # Apply search filter
    if search:
        search_lower = search.lower()
        shops = [
            s for s in shops
            if search_lower in s["name"].lower() or search_lower in s["address"].lower()
        ]
    
    return shops

@router.get("/navigate")
async def navigate_to_shop(shop_id: str, lat: Optional[float] = None, lng: Optional[float] = None):
    """Bridge endpoint for navigation"""
    return await get_shop_navigation(shop_id, lat, lng)

@router.get("/{shop_id}/navigation")
async def get_shop_navigation(
    shop_id: str,
    customer_lat: Optional[float] = Query(None),
    customer_lng: Optional[float] = Query(None)
):
    """Get navigation link for a specific shop with optional origin coordinates"""
    
    shop = get_hydrated_shop(shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    
    dest_lat = shop["coordinates"]["lat"]
    dest_lng = shop["coordinates"]["lng"]
    
    # Base URL with destination
    google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={dest_lat},{dest_lng}&travelmode=driving"
    
    # Add origin if customer coordinates are provided
    if customer_lat is not None and customer_lng is not None:
        google_maps_url += f"&origin={customer_lat},{customer_lng}"
    
    return {
        "shopId": shop_id,
        "name": shop["name"],
        "destination": {"lat": dest_lat, "lng": dest_lng},
        "origin": {"lat": customer_lat, "lng": customer_lng} if customer_lat else None,
        "googleMapsUrl": google_maps_url
    }

@router.get("/{shop_id}", response_model=dict)
async def get_shop(shop_id: str):
    shop = get_hydrated_shop(shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    return shop

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_shop_route(shop: CreateShopRequest):
    """Create a new shop (Owner only)"""
    shop_data = shop.model_dump()
    new_shop = create_shop(shop_data)
    if not new_shop:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create shop"
        )
    return new_shop

@router.put("/{shop_id}", response_model=dict)
async def update_shop_route(shop_id: str, update_data: UpdateShopRequest):
    """Update shop information (Owner only)"""
    data = update_data.model_dump(exclude_unset=True)
    updated = update_shop(shop_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    return updated

@router.delete("/{shop_id}")
async def delete_shop_route(shop_id: str):
    """Delete a shop (Owner only)"""
    if not delete_shop(shop_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    return {"message": "Shop deleted successfully"}

@router.get("/{shop_id}/staff", response_model=List[dict])
async def get_shop_staff(shop_id: str):
    """Get all staff members for a shop with their actual profile photos"""
    from app.db import get_staff_full_profile
    
    shop = get_hydrated_shop(shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    
    # Get staff list from shop
    staff_list = shop.get("staff", [])
    
    # Enrich each staff member with their actual profile data
    enriched_staff = []
    for staff_member in staff_list:
        staff_id = staff_member.get("id")
        if staff_id:
            # Fetch full profile to get actual imageUrl
            full_profile = get_staff_full_profile(staff_id)
            if full_profile:
                # Use actual profile photo, fallback to shop's staff data
                staff_member["imageUrl"] = full_profile.get("imageUrl", staff_member.get("imageUrl", "https://picsum.photos/200/200"))
                staff_member["name"] = full_profile.get("name", staff_member.get("name"))
        enriched_staff.append(staff_member)
    
    return enriched_staff

@router.post("/{shop_id}/staff-create")
async def create_staff_for_shop(shop_id: str, staff_data: CreateStaffRequest):
    """Create a new user and staff profile, then link to shop"""
    # 1. Create User
    user_data = {
        "name": staff_data.name,
        "phone": staff_data.phone,
        "email": staff_data.email or f"{staff_data.name.lower().replace(' ', '.')}@temp.com",
        "role": "BARBER",
        "password": "hashed_default_password",
        "permissions": {"location": True, "notifications": True}
    }
    user = add_user(user_data)
    
    # 2. Update/Create Staff Profile
    staff = update_staff_profile(user["id"], {
        "name": staff_data.name,
        "shopId": shop_id,
        "role": "Barber",
        "imageUrl": user.get("profilePhoto") or "https://picsum.photos/200/200"
    })
    
    return {"message": "Staff created and added", "staff": staff}

@router.post("/{shop_id}/staff/{staff_id}")
async def add_staff_to_shop(shop_id: str, staff_id: str):
    """Add a staff member to a shop"""
    updated = update_staff_profile(staff_id, {"shopId": shop_id})
    if not updated:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"message": "Staff added successfully", "staff": updated}

@router.delete("/{shop_id}/staff/{staff_id}")
async def remove_staff_from_shop(shop_id: str, staff_id: str):
    """Remove a staff member from a shop"""
    updated = update_staff_profile(staff_id, {"shopId": None})
    if not updated:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"message": "Staff removed successfully"}

@router.get("/{shop_id}/services", response_model=List[dict])
async def get_shop_services(shop_id: str):
    """Get all services offered by a shop"""
    shop = get_hydrated_shop(shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    return shop.get("services", [])

@router.get("/{shop_id}/services/popular", response_model=List[dict])
async def get_popular_services(shop_id: str):
    """Get services sorted by booking frequency (most popular first)"""
    from app.database.database import SessionLocal
    from app.database import models
    from collections import Counter
    
    # Verify shop exists
    shop = get_hydrated_shop(shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    db = SessionLocal()
    try:
        # Get all bookings for this shop
        bookings = db.query(models.Booking).filter(
            models.Booking.shopId == shop_id,
            models.Booking.status.in_(["CONFIRMED", "COMPLETED", "IN_PROGRESS"])
        ).all()
        
        # Count service frequency
        service_counter = Counter()
        for booking in bookings:
            if booking.services:
                # services is a JSON array of service IDs
                for service_id in booking.services:
                    service_counter[service_id] += 1
        
        # Get all services and add booking counts
        services = shop.get("services", [])
        for service in services:
            service["bookingCount"] = service_counter.get(service["id"], 0)
        
        # Sort by booking count (descending), then by name for stable sort
        services.sort(key=lambda s: (-s["bookingCount"], s["name"]))
        
        return services
        
    finally:
        db.close()


@router.post("/{shop_id}/services")
async def add_service_to_shop(shop_id: str, service: AddServiceRequest):
    """Add a new service to a shop"""
    service_data = service.model_dump()
    service_data["shopId"] = shop_id
    if not service_data.get("imageUrl"):
        service_data["imageUrl"] = "https://picsum.photos/400/300"
    return add_service(service_data)

@router.put("/{shop_id}/services/{service_id}")
async def update_service_route(shop_id: str, service_id: str, service_data: UpdateServiceRequest):
    """Update a service details"""
    from app.database.database import get_db
    from app.routers.owner import create_audit_log
    
    # Get the service before update to compare changes
    shop = get_hydrated_shop(shop_id)
    old_service = None
    if shop and 'services' in shop:
        old_service = next((s for s in shop['services'] if s.get('id') == service_id), None)
    
    # Update the service
    data = service_data.model_dump(exclude_unset=True)
    updated = update_service(service_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Create audit log for price changes
    if old_service and 'price' in data and old_service.get('price') != data['price']:
        db_gen = get_db()
        db = next(db_gen)
        try:
            create_audit_log(
                db=db,
                actor_id=shop.get('ownerId'),
                actor_role="OWNER",
                action_type="price_change",
                entity_type="service",
                entity_id=service_id,
                details={
                    "serviceName": old_service.get('name'),
                    "oldPrice": old_service.get('price'),
                    "newPrice": data['price']
                },
                shop_id=shop_id
            )
        finally:
            db.close()
    
    return updated

@router.delete("/{shop_id}/services/{service_id}")
async def delete_shop_service(shop_id: str, service_id: str):
    """Delete a service from a shop"""
    from app.database.database import get_db
    from app.routers.owner import create_audit_log
    
    # Get service info before deletion for logging
    shop = get_hydrated_shop(shop_id)
    service_name = "Unknown"
    if shop and 'services' in shop:
        service = next((s for s in shop['services'] if s.get('id') == service_id), None)
        if service:
            service_name = service.get('name', "Unknown")

    if delete_service(service_id):
        # Log the deletion
        db_gen = get_db()
        db = next(db_gen)
        try:
            create_audit_log(
                db=db,
                actor_id=shop.get('ownerId') if shop else None,
                actor_role="OWNER",
                action_type="service_delete",
                entity_type="service",
                entity_id=service_id,
                details={"serviceName": service_name},
                shop_id=shop_id
            )
        finally:
            db.close()
        return {"message": "Service removed successfully"}
    raise HTTPException(status_code=404, detail="Service not found")

@router.post("/{shop_id}/photos")
async def add_photo_to_shop_route(shop_id: str, photo: AddPhotoRequest):
    """Add a photo to a shop's gallery"""
    photos = add_shop_photo(shop_id, photo.photoUrl)
    if photos is None:
        raise HTTPException(status_code=404, detail="Shop not found")
    return {"message": "Photo added successfully", "photos": photos}

@router.get("/detect-by-phone")
async def get_shops_by_staff_phone(phone: str):
    """Detect which shops a staff member belongs to based on their registered phone number"""
    user = get_user_by_phone(phone)
    if not user:
        raise HTTPException(status_code=404, detail="No staff member found with this phone number")
    
    profile = get_staff_full_profile(user["id"])
    if not profile or not profile.get("shop"):
        return {
            "staffId": user["id"],
            "name": user["name"],
            "shops": []
        }
    
    return {
        "staffId": profile["id"],
        "name": profile["name"],
        "shops": [profile["shop"]]
    }

@router.get("/owned-by/{owner_id}", response_model=List[dict])
async def get_shops_by_owner(owner_id: str):
    """Get all shops owned by a specific user"""
    from app.database.database import SessionLocal
    from app.database import models
    db = SessionLocal()
    try:
        shop_ids = [s.id for s in db.query(models.Shop.id).filter(models.Shop.ownerId == owner_id).all()]
        return [get_hydrated_shop(sid) for sid in shop_ids]
    finally:
        db.close()

@router.get("/staff/{staff_id}/profile")
async def get_staff_profile(staff_id: str):
    """Get detailed profile for a staff member including experience, portfolio, and shop context"""
    profile = get_staff_full_profile(staff_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return profile

@router.put("/staff/{staff_id}/profile")
async def update_staff_profile_route(staff_id: str, data: UpdateStaffProfileRequest):
    from app.db import update_user, update_staff_profile, get_staff_full_profile
    
    print(f"[UPDATE_STAFF_PROFILE] Received data: {data.model_dump()}")
    
    # Resolve the REAL User ID first
    # staff_id could be the Staff ID (most likely) or User ID
    # utilizing get_staff_full_profile's logic to find the link
    profile = get_staff_full_profile(staff_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Staff member not found")
        
    real_user_id = profile["userId"] if profile.get("userId") else profile["id"]
    real_staff_id = profile["id"] # The ID of the Staff record specifically

    # 1. Update User Table
    user_updates = {}
    if data.name: user_updates["name"] = data.name
    if data.phone: user_updates["phone"] = data.phone
    if data.profilePhoto is not None: user_updates["profilePhoto"] = data.profilePhoto
    if data.portfolio: user_updates["portfolio"] = data.portfolio
    
    # Sync professional fields to user table for redundancy/consistency
    if data.experience is not None: user_updates["experience"] = data.experience
    if data.description: user_updates["about"] = data.description
    
    if user_updates:
        print(f"[UPDATE_STAFF_PROFILE] Updating user table: {user_updates}")
        update_user(real_user_id, user_updates)

    # 2. Update Staff Table (Professional Details)
    staff_updates = {}
    if data.experience is not None: staff_updates["experience"] = data.experience
    if data.description: staff_updates["description"] = data.description
    if data.workPhotos is not None: 
        staff_updates["workPhotos"] = data.workPhotos
        print(f"[UPDATE_STAFF_PROFILE] workPhotos to update: {data.workPhotos}")
    if data.profilePhoto is not None: staff_updates["imageUrl"] = data.profilePhoto  # Allow empty string to remove photo
    if data.services is not None: staff_updates["services"] = data.services
    if data.skills is not None: 
        staff_updates["skills"] = data.skills
        print(f"[UPDATE_STAFF_PROFILE] skills to update: {data.skills}")
    
    if data.isAvailable is not None: staff_updates["isAvailable"] = data.isAvailable

    if data.isAvailable is not None and profile.get("isAvailable") != data.isAvailable:
        from app.database.database import get_db
        from app.routers.owner import create_audit_log
        db_gen = get_db()
        db = next(db_gen)
        try:
            create_audit_log(
                db=db,
                actor_id=None, # System or staff themselves
                actor_role="BARBER",
                action_type="staff_disable" if not data.isAvailable else "staff_enable",
                entity_type="staff",
                entity_id=real_staff_id,
                details={"staffName": profile.get("name"), "status": "unavailable" if not data.isAvailable else "available"},
                shop_id=profile.get("shopId")
            )
        finally:
            db.close()
    
    if staff_updates:
        print(f"[UPDATE_STAFF_PROFILE] Updating staff table: {staff_updates}")
        print(f"[UPDATE_STAFF_PROFILE] Using real_staff_id: {real_staff_id}")
        updated_staff = update_staff_profile(real_staff_id, staff_updates)
        if not updated_staff:
             # If doesn't exist, we might need to create it
             pass
    
    # 3. Update Shop's Staff Array (so Staff Management shows correct photos)
    if data.profilePhoto is not None and profile.get("shopId"):
        from app.db import get_shop, update_shop
        shop = get_shop(profile["shopId"])
        if shop and "staff" in shop:
            # Find and update this staff member in the shop's staff array
            staff_array = shop["staff"]
            for i, staff_member in enumerate(staff_array):
                if staff_member.get("id") == real_staff_id or staff_member.get("userId") == real_user_id:
                    # Update the imageUrl in the shop's staff array
                    staff_array[i]["imageUrl"] = data.profilePhoto
                    if data.name:
                        staff_array[i]["name"] = data.name
                    break
            # Save updated shop
            update_shop(profile["shopId"], {"staff": staff_array})
            print(f"[UPDATE_STAFF_PROFILE] Updated shop's staff array with new imageUrl")
    
    return {"message": "Staff profile updated successfully"}
