from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import os
from jose import JWTError, jwt

from app.services.otp_service import otp_service
from app.repositories.user_repository import UserRepository
from app.repositories.shop_repository import ShopRepository
from app.database import models

router = APIRouter(prefix="/auth", tags=["authentication"])

# Config
SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey") # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60 # 30 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/otp/verify") # Placeholder URL

# Models
class OTPRequest(BaseModel):
    phone: str

class OTPVerifyRequest(BaseModel):
    phone: str
    code: str

class OTPUpdateRequest(BaseModel):
    new_phone: str

class OTPUpdateVerifyRequest(BaseModel):
    new_phone: str
    code: str

class RoleSelectionRequest(BaseModel):
    user_id: str
    role: str # OWNER, BARBER, CUSTOMER
    shop_id: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class AuthResponse(BaseModel):
    user: Optional[dict] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    roles: Optional[List[dict]] = None
    message: str
    action: str # "LOGIN", "SELECT_ROLE", "REGISTER"
    
class UserPayload(BaseModel):
    sub: str
    role: Optional[str] = None
    shop_id: Optional[str] = None

# Utils
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def normalize_phone(phone: str) -> str:
    return "".join(filter(str.isdigit, str(phone)))

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # token_data = UserPayload(**payload) # Optional validation
    except JWTError:
        raise credentials_exception
        
    user = UserRepository.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user
    
async def get_current_role(token: str = Depends(oauth2_scheme)):
    """Extract role info from token without full DB lookup if possible, or validate."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Routes
@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_otp(data: OTPRequest):
    """Request OTP for phone number."""
    phone = normalize_phone(data.phone)
    if len(phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number")
        
    success = otp_service.request_otp(phone)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send OTP")
        
    return {"message": "OTP sent successfully"}

@router.post("/otp/verify", response_model=AuthResponse)
async def verify_otp(data: OTPVerifyRequest):
    """Verify OTP and log in/register user."""
    phone = normalize_phone(data.phone)
    
    if not otp_service.verify_otp(phone, data.code):
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    # Get User
    user_dict = UserRepository.get_by_phone(phone)
    
    if not user_dict:
        # User NOT found -> Return Registration Token
        # Create temporary token with phone number
        registration_token = create_access_token(
            data={"sub": phone, "scope": "registration", "role": "GUEST"},
            expires_delta=timedelta(minutes=30) # 30 mins to complete registration
        )
        
        return {
            "user": None,
            "access_token": registration_token,
            "token_type": "bearer",
            "message": "User not found, please register.",
            "action": "REGISTER"
        }
        
    # User exists. Check Roles.
    # ... (rest of role checking logic remains same) ...

    # Let's perform a direct DB query here to get efficient role list
    with UserRepository.get_session() as db:
        user_obj = db.query(models.User).filter(models.User.id == user_dict["id"]).first()
        raw_roles = user_obj.roles # List of UserRole
        
        roles_list = []
        for ur in user_obj.roles:
            if ur.active:
                shop_name = None
                if ur.shop_id:
                     shop = db.query(models.Shop).filter(models.Shop.id == ur.shop_id).first()
                     if shop:
                         shop_name = shop.name
                
                roles_list.append({
                    "role": ur.role.name,
                    "shop_id": ur.shop_id,
                    "shop_name": shop_name
                })
            
    # Decision Logic
    # 1. If only CUSTOMER -> Auto Login
    if len(roles_list) == 1 and roles_list[0]["role"] == "CUSTOMER":
        # Generate Token
        access_token = create_access_token(
            data={"sub": user_dict["id"], "role": "CUSTOMER"}
        )
        return {
            "user": user_dict,
            "access_token": access_token,
            "token_type": "bearer",
            "message": "Login successful",
            "action": "LOGIN"
        }
        
    # 2. If multiple roles (Result of Barber/Owner usage) -> Return Choice
    return {
        "user": user_dict, # Contains basic info
        "roles": roles_list,
        "message": "Select a role to continue",
        "action": "SELECT_ROLE"
    }

class RegisterRequest(BaseModel):
    name: str
    email: Optional[str] = None
    role: str # OWNER, BARBER, CUSTOMER
    shop_name: Optional[str] = None 
    shop_address: Optional[str] = None
    # Legal Consent
    agreedToPrivacy: bool = False
    agreedToTerms: bool = False
    legalConsentName: Optional[str] = None
    legalConsentPlace: Optional[str] = None
    legalConsentTimestamp: Optional[str] = None
    
@router.post("/register", response_model=AuthResponse)
async def complete_registration(data: RegisterRequest, token: str = Depends(oauth2_scheme)):
    """Complete registration using temporary token."""
    print(f"DEBUG: complete_registration called. Data: {data}")
    
    # 1. Verify Registration Token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone = payload.get("sub")
        scope = payload.get("scope")
        print(f"DEBUG: Token payload: {payload}")
        
        if not phone or scope != "registration":
             print("DEBUG: Invalid token scope or phone missing")
             raise HTTPException(status_code=401, detail="Invalid registration token")
             
    except JWTError as e:
        print(f"DEBUG: JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

    # 2. Check if user exists (Double check)
    if UserRepository.get_by_phone(phone):
         print(f"DEBUG: User already exists for phone {phone}")
         raise HTTPException(status_code=400, detail="User already exists")

    # 3. Create User
    user_id = str(uuid.uuid4())
    # Handle email if provided, else placeholder
    email = data.email
    if not email:
        email = f"{phone}_{uuid.uuid4().hex[:8]}@placeholder.com"
        
    new_user_data = {
        "id": user_id,
        "phone": phone,
        "name": data.name,
        "email": email,
        "role": data.role,
        "fcmToken": None
    }
    
    try:
        print(f"DEBUG: Creating user with data: {new_user_data}")
        user_dict = UserRepository.create(new_user_data)
        print(f"DEBUG: User created: {user_dict}")
        
        # If Owner, create shop? 
        # Usually registration flow might involve shop creation separately.
        # But for MVP, if Role is Owner, we might need to handle shop creation here or later.
        # Based on "RegistrationFlow", it asks for Shop Name.
        
        if data.role == "OWNER" and data.shop_name:
             # Create shop logic... 
             # For now, let's assume ShopRepository.create handles it or we call it here.
             # We need ShopRepository.create(owner_id, shop_data)
             pass 

        # Generate Access Token
        access_token = create_access_token(
            data={"sub": user_id, "role": data.role}
        )
        
        return {
            "user": user_dict,
            "access_token": access_token,
            "token_type": "bearer",
            "message": "Registration successful",
            "action": "LOGIN"
        }
        
    except Exception as e:
        print(f"DEBUG: Registration Exception: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login/select-role", response_model=AuthResponse)
async def select_role(data: RoleSelectionRequest):
    """Login as a specific role."""
    
    with UserRepository.get_session() as db:
        # Verify ownership
        # We need to find a UserRole that matches user_id, role name (or ID?), and shop_id
        # Request says "role: OWNER | BARBER".
        
        query = db.query(models.UserRole).join(models.Role).filter(
            models.UserRole.user_id == data.user_id,
            models.Role.name == data.role,
            models.UserRole.active == True
        )
        
        if data.shop_id:
             query = query.filter(models.UserRole.shop_id == data.shop_id)
             
        user_role = query.first()
        
        if not user_role:
             raise HTTPException(status_code=401, detail="Invalid role selection")
             
        # Generate Scoped Token
        token_data = {
            "sub": data.user_id,
            "role": data.role,
            "shop_id": data.shop_id
        }
        access_token = create_access_token(data=token_data)
        
        # Get User Dict (backward compat)
        user_dict = UserRepository.get_by_id(data.user_id)
        # Maybe patch user_dict role to match selected?
        user_dict["role"] = data.role
        
        return {
            "user": user_dict,
            "access_token": access_token,
            "token_type": "bearer",
            "message": f"Logged in as {data.role}",
            "action": "LOGIN"
        }
        return {
            "user": user_dict,
            "access_token": access_token,
            "token_type": "bearer",
            "message": f"Logged in as {data.role}",
            "action": "LOGIN"
        }

@router.post("/otp/request-update", status_code=status.HTTP_200_OK)
async def request_update_otp(data: OTPUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Request OTP for UPDATING phone number (Authenticated user only)."""
    new_phone = normalize_phone(data.new_phone)
    if len(new_phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    
    # Check if new phone is already occupied by ANOTHER user
    existing_user = UserRepository.get_by_phone(new_phone)
    if existing_user and existing_user['id'] != current_user['id']:
        raise HTTPException(status_code=400, detail="Phone number already in use by another account")
        
    success = otp_service.request_otp(new_phone)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send OTP")
        
    return {"message": "OTP sent to new number"}

@router.post("/otp/verify-update", status_code=status.HTTP_200_OK)
async def verify_update_otp(data: OTPUpdateVerifyRequest, current_user: dict = Depends(get_current_user)):
    """Verify OTP and update user's phone number."""
    new_phone = normalize_phone(data.new_phone)
    
    if not otp_service.verify_otp(new_phone, data.code):
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    # Check again for conflict (just in case)
    existing_user = UserRepository.get_by_phone(new_phone)
    if existing_user and existing_user['id'] != current_user['id']:
        raise HTTPException(status_code=400, detail="Phone number already in use by another account")
    
    # Update User Phone
    updated_user = UserRepository.update(current_user['id'], {"phone": new_phone})
    
    return {
        "message": "Phone number updated successfully",
        "user": updated_user
    }
