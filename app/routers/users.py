from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.db import get_user_by_id, update_user

router = APIRouter(prefix="/users", tags=["users"])

class FCMTokenRequest(BaseModel):
    fcmToken: str

@router.post("/{user_id}/fcm-token")
async def update_fcm_token(user_id: str, data: FCMTokenRequest):
    """Update user's FCM token for push notifications"""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updated_user = update_user(user_id, {"fcmToken": data.fcmToken})
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update FCM token"
        )
    
    return {"message": "FCM token updated successfully"}
