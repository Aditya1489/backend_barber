from pydantic import BaseModel, EmailStr
from typing import List, Optional
from enum import Enum

class AppRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    BARBER = "BARBER"
    OWNER = "OWNER"

class AppointmentStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

class ServiceBase(BaseModel):
    name: str
    price: float
    duration: int
    imageUrl: Optional[str] = None

class Service(ServiceBase):
    id: str

class StaffBase(BaseModel):
    name: str
    role: str
    experience: int
    rating: float
    reviewsCount: int
    description: str
    imageUrl: str
    workPhotos: List[str]
    services: List[str]

class Staff(StaffBase):
    id: str

class BarberShopBase(BaseModel):
    name: str
    address: str
    description: str
    rating: float
    reviewsCount: int
    photos: List[str]
    coordinates: dict

class BarberShop(BarberShopBase):
    id: str
    staff: List[Staff]
    services: List[Service]

class AppointmentBase(BaseModel):
    shopId: str
    staffId: str
    customerId: str
    services: List[str]
    date: str
    timeSlot: str
    status: AppointmentStatus
    totalAmount: float
    totalDuration: int

class Appointment(AppointmentBase):
    id: str
    bookedAt: str

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    role: AppRole

class User(UserBase):
    id: str
    profilePhoto: Optional[str] = None
    permissions: dict
