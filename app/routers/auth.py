from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid
import bcrypt

router = APIRouter(prefix="/auth", tags=["authentication"])

from app.db import get_user_by_email, get_user_by_phone, update_user, add_user

# Request/Response Models
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    role: str = "CUSTOMER"  # CUSTOMER, BARBER, OWNER

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict
    message: str

class RegisterResponse(BaseModel):
    user: dict
    message: str

class GoogleAuthRequest(BaseModel):
    idToken: str
    role: str = "CUSTOMER"

# Routes
@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest):
    """Register a new user"""
    
    # Check if user already exists
    existing_user_email = get_user_by_email(data.email)
    if existing_user_email:
        # If it's a real user with this email, error out
        if "temp.com" not in data.email: # Simple check if it was a placeholder email
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

    # Check if user exists by PHONE (the critical link for Staff)
    # Normalize phone numbers for comparison (remove spaces, dashes, parentheses)
    def normalize_phone(p):
        return "".join(filter(str.isdigit, str(p))) if p else ""

    input_phone = normalize_phone(data.phone)
    existing_user_phone = get_user_by_phone(data.phone) # We can also try normalized if needed, but the helper handles exact for now

    hashed_pwd = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    if existing_user_phone:
        # Use the existing ID to maintain links (e.g. to a Shop)
        user_id = existing_user_phone["id"]
        # Update details
        update_data = {
            "name": data.name,
            "email": data.email,
            "password": hashed_pwd,
            "role": data.role,
            "createdAt": datetime.utcnow()
        }
        
        # Ensure permissions are set
        if "permissions" not in existing_user_phone or not existing_user_phone["permissions"]:
             update_data["permissions"] = {
                "location": False,
                "notifications": False,
                "camera": False,
                "storage": False
            }
            
        new_user = update_user(user_id, update_data)
        # We don't create a new entry, just update
    else:
        # Create new user
        user_id = str(uuid.uuid4())
        new_user = {
            "id": user_id,
            "name": data.name,
            "email": data.email,
            "phone": data.phone,
            "password": hashed_pwd,
            "role": data.role,
            "profilePhoto": None,
            "permissions": {
                "location": False,
                "notifications": False,
                "camera": False,
                "storage": False
            },
            "createdAt": datetime.utcnow()
        }
        new_user = add_user(new_user)
    
    # Remove password from response
    user_response = {k: v for k, v in new_user.items() if k != "password"}
    
    return {
        "user": user_response,
        "message": "Registration successful"
    }

@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    """Login with email and password"""
    
    # Check if user exists
    user = get_user_by_email(data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not bcrypt.checkpw(data.password.encode('utf-8'), user["password"].encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Generate token (in production, use JWT)
    token = f"mock_token_{user['id']}_{datetime.utcnow().timestamp()}"
    
    # Remove password from response
    user_response = {k: v for k, v in user.items() if k != "password"}
    
    return {
        "token": token,
        "user": user_response,
        "message": "Login successful"
    }

@router.post("/google", response_model=LoginResponse)
async def google_auth(data: GoogleAuthRequest):
    """Authenticate with Google"""
    
    # In production, verify the idToken with Google
    # For now, create a mock user
    
    email = f"google_user_{uuid.uuid4().hex[:8]}@gmail.com"
    
    # Check if user exists
    user = get_user_by_email(email)
    if user:
        pass
    else:
        # Create new user
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "name": "Google User",
            "email": email,
            "phone": "",
            "password": "",
            "role": data.role,
            "profilePhoto": "https://picsum.photos/200/200?random=" + str(uuid.uuid4().hex[:4]),
            "permissions": {
                "location": False,
                "notifications": False,
                "camera": False,
                "storage": False
            },
            "createdAt": datetime.utcnow()
        }
        user = add_user(user)
    
    # Generate token
    token = f"mock_token_{user['id']}_{datetime.utcnow().timestamp()}"
    
    # Remove password from response
    user_response = {k: v for k, v in user.items() if k != "password"}
    
    return {
        "token": token,
        "user": user_response,
        "message": "Google authentication successful"
    }

@router.post("/logout")
async def logout():
    """Logout user"""
    return {"message": "Logout successful"}

@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    """Send password reset email"""
    
    user = get_user_by_email(email)
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # In production, send actual email with reset link
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password")
async def reset_password(token: str, new_password: str):
    """Reset password with token"""
    
    # In production, verify token and update password
    return {"message": "Password reset successful"}

@router.get("/verify-token")
async def verify_token(token: str):
    """Verify if token is valid"""
    
    # In production, verify JWT token
    if token.startswith("mock_token_"):
        return {"valid": True, "message": "Token is valid"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token"
    )
