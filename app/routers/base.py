from fastapi import APIRouter
from typing import List
# from app.schemas.schemas import BarberShop, Appointment, User, Staff, Service # These might not be used or exist in the new structure
from app.db import get_bookings

router = APIRouter()

@router.get("/appointments")
async def get_appointments(user_id: str):
    """Bridge endpoint for customer appointments"""
    # Ensure we use the correct keyword argument for the DB helper
    return get_bookings(customer_id=user_id)
