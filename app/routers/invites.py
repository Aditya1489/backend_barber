from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from app.routers.auth import get_current_user, get_current_role
from app.repositories.invite_repository import InviteRepository
from app.repositories.user_repository import UserRepository
from app.database import models

router = APIRouter(prefix="/invites", tags=["invites"])

class CreateInviteRequest(BaseModel):
    phone: str
    shop_id: str
    role: str = "BARBER"

class InviteResponse(BaseModel):
    id: str
    phone: str
    shop_id: str
    role: str
    status: str
    expires_at: datetime

@router.post("/", response_model=InviteResponse)
async def create_invite(
    data: CreateInviteRequest,
    current_role: dict = Depends(get_current_role)
):
    """
    Create a staff invite. 
    Requires OWNER role for the specific shop_id.
    """
    # Verify Permissions
    role = current_role.get("role")
    shop_id = current_role.get("shop_id")
    
    if role != "OWNER":
        raise HTTPException(status_code=403, detail="Only owners can invite staff")
        
    if shop_id != data.shop_id:
        # Strict scoping Check
        # If the token shop_id doesn't match the target shop_id
        raise HTTPException(status_code=403, detail="Not authorized for this shop")

    # Create Invite
    invite = InviteRepository.create(data.shop_id, data.phone, data.role)
    return invite

@router.get("/my", response_model=List[InviteResponse])
async def get_my_invites(
    current_user: dict = Depends(get_current_user)
):
    """Get pending invites for the authenticated user's phone number."""
    # current_user is a dict from UserRepository._entity_to_dict
    phone = current_user["phone"]
    invites = InviteRepository.get_pending_by_phone(phone)
    return invites

@router.post("/{invite_id}/accept")
async def accept_invite(
    invite_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept an invite using the authenticated user's identity."""
    # 1. Verify invite
    invite = InviteRepository.get_by_id(invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
        
    if invite["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="Invite is not pending")
        
    if invite["phone"] != current_user["phone"]:
        raise HTTPException(status_code=403, detail="This invite is not for you")

    # 2. Logic: Create UserRole and Profile
    with UserRepository.get_session() as db:
        # Find Role Object
        role_obj = db.query(models.Role).filter(models.Role.name == invite["role"]).first()
        if not role_obj:
             raise HTTPException(500, "Role configuration error")
             
        # Check if user already has this role for this shop
        existing_role = db.query(models.UserRole).filter(
            models.UserRole.user_id == current_user["id"],
            models.UserRole.shop_id == invite["shop_id"],
            models.UserRole.role_id == role_obj.id
        ).first()
        
        if not existing_role:
            # Create User Role
            user_role = models.UserRole(
                user_id=current_user["id"],
                role_id=role_obj.id,
                shop_id=invite["shop_id"]
            )
            db.add(user_role)
            
            # Create Staff Profile
            # Check if Staff profile exists for this shop?
            # We assume One-User-Per-Shop-As-Staff, so we look for existing staff in this shop with this user
            existing_staff = db.query(models.Staff).filter(
                models.Staff.userId == current_user["id"],
                models.Staff.shopId == invite["shop_id"]
            ).first()
            
            if not existing_staff:
                staff = models.Staff(
                    id=str(uuid.uuid4()),
                    userId=current_user["id"],
                    shopId=invite["shop_id"],
                    name=current_user["name"] or "Staff Member",
                    role="Barber",
                    imageUrl=current_user.get("profilePhoto") # Inherit photo if available? or None
                )
                db.add(staff)
            
            db.commit()

    # Mark invite as accepted
    InviteRepository.accept_invite(invite_id)
    
    return {"message": "Invite accepted", "action": "REFRESH_ROLES"}
