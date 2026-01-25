from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from app.schemas.schemas import User

router = APIRouter(prefix="/profile", tags=["profile"])

from app.db import get_user_by_id, update_user

# Request/Response Models
class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    profilePhoto: Optional[str] = None
    experience: Optional[int] = None
    about: Optional[str] = None
    portfolio: Optional[list[str]] = None
    location: Optional[dict] = None

class UpdatePermissionsRequest(BaseModel):
    location: Optional[bool] = None
    notifications: Optional[bool] = None
    camera: Optional[bool] = None
    storage: Optional[bool] = None

class ProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    role: str
    profilePhoto: Optional[str] = None
    permissions: Dict[str, bool]
    experience: Optional[int] = None
    about: Optional[str] = None
    portfolio: Optional[list[str]] = None
    location: Optional[dict] = None

# Routes
@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str):
    """Get user profile by ID"""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/{user_id}", response_model=ProfileResponse)
async def update_profile(user_id: str, profile_data: UpdateProfileRequest):
    """Update user profile information"""
    data = profile_data.model_dump(exclude_unset=True)
    updated_user = update_user(user_id, data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return updated_user

@router.get("/{user_id}/permissions", response_model=Dict[str, bool])
async def get_permissions(user_id: str):
    """Get user permissions"""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user.get("permissions", {})

@router.put("/{user_id}/permissions", response_model=Dict[str, bool])
async def update_permissions(user_id: str, permissions_data: UpdatePermissionsRequest):
    """Update user permissions"""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    permissions = user.get("permissions", {}).copy()
    if permissions_data.location is not None: permissions["location"] = permissions_data.location
    if permissions_data.notifications is not None: permissions["notifications"] = permissions_data.notifications
    if permissions_data.camera is not None: permissions["camera"] = permissions_data.camera
    if permissions_data.storage is not None: permissions["storage"] = permissions_data.storage
    
    updated_user = update_user(user_id, {"permissions": permissions})
    return updated_user["permissions"]

@router.post("/{user_id}/photo", response_model=ProfileResponse)
async def upload_profile_photo(user_id: str, photo_url: str):
    """Upload/update profile photo"""
    updated_user = update_user(user_id, {"profilePhoto": photo_url})
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return updated_user
