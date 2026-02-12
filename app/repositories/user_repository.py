"""
User repository - handles all user-related database operations.
"""
from app.repositories.base import BaseRepository
from app.database import models
from sqlalchemy.orm import joinedload
from datetime import datetime

class UserRepository(BaseRepository):
    """Repository for User entity operations."""
    
    @classmethod
    def _entity_to_dict(cls, user):
        """Convert User entity to backward-compatible dict."""
        if not user:
            return None
            
        data = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            # "password": user.password, # Removed
            "fcmToken": user.fcmToken,
            "createdAt": user.createdAt,
            "agreedToPrivacy": user.agreed_to_privacy,
            "agreedToTerms": user.agreed_to_terms,
            "legalConsentName": user.legal_consent_name,
            "legalConsentPlace": user.legal_consent_place,
            "legalConsentTimestamp": user.legal_consent_timestamp.isoformat() if user.legal_consent_timestamp else None,
        }
        
        # Resolve distinct roles
        roles = [r.role.name for r in user.roles] if user.roles else []
        # Backward compatibility: Pick primary role
        # Priority: OWNER > BARBER > CUSTOMER
        if "OWNER" in roles:
            data["role"] = "OWNER"
        elif "BARBER" in roles:
            data["role"] = "BARBER"
        else:
            data["role"] = "CUSTOMER" # Default
            
        # Resolve Profile Data based on effective role
        if data["role"] == "CUSTOMER" and user.customer_profile:
            data["profilePhoto"] = user.customer_profile.profile_photo
            data["preferences"] = user.customer_profile.preferences
            data["loyaltyPoints"] = user.customer_profile.loyalty_points
            
        elif data["role"] == "OWNER" and user.owner_profile:
            data["profilePhoto"] = user.owner_profile.profile_photo
            data["permissions"] = user.owner_profile.permissions
            
        elif data["role"] == "BARBER" and user.staff_profile:
            # Handle list of profiles (pick first for backward compatibility)
            profile = user.staff_profile[0] if isinstance(user.staff_profile, list) and user.staff_profile else user.staff_profile
            # Note: SQLAlchemy might return InstrumentedList which behaves like list. 
            # If relation was not loaded, it might be something else, but we use joinedload.
            
            if isinstance(profile, list): # Double check if logic above failed
                 profile = profile[0] if profile else None
                 
            # If it was a single object before, it might still vary during migration or test mocks.
            # But with uselist=True, it should be iterable.
            
            if profile and not isinstance(profile, list):
                data["profilePhoto"] = profile.imageUrl
                data["experience"] = profile.experience
                data["about"] = profile.description
            # Portfolio mapping might need adjustment depending on how it was stored
            # data["portfolio"] = ...
            
        return data

    @classmethod
    def get_by_email(cls, email: str):
        """Get user by email address."""
        with cls.get_session() as db:
            user = db.query(models.User).options(
                joinedload(models.User.roles).joinedload(models.UserRole.role),
                joinedload(models.User.customer_profile),
                joinedload(models.User.owner_profile),
                joinedload(models.User.staff_profile)
            ).filter(models.User.email == email).first()
            
            return cls._entity_to_dict(user)
    
    @classmethod
    def get_by_id(cls, user_id: str):
        """Get user by ID."""
        with cls.get_session() as db:
            user = db.query(models.User).options(
                joinedload(models.User.roles).joinedload(models.UserRole.role),
                joinedload(models.User.customer_profile),
                joinedload(models.User.owner_profile),
                joinedload(models.User.staff_profile)
            ).filter(models.User.id == user_id).first()
            
            return cls._entity_to_dict(user)
    
    @classmethod
    def get_by_phone(cls, phone: str):
        """Get user by phone number."""
        with cls.get_session() as db:
            user = db.query(models.User).options(
                joinedload(models.User.roles).joinedload(models.UserRole.role),
                joinedload(models.User.customer_profile),
                joinedload(models.User.owner_profile),
                joinedload(models.User.staff_profile)
            ).filter(models.User.phone == phone).first()
            
            return cls._entity_to_dict(user)
    
    @classmethod
    def create(cls, user_data: dict):
        """Create a new user with role and profile."""
        print(f"DEBUG: UserRepository.create called with data: {user_data}")
        start_role = user_data.pop("role", "CUSTOMER")
        profile_photo = user_data.pop("profilePhoto", None)
        permissions = user_data.pop("permissions", {})
        
        # Filter core user fields
        core_fields = [
            "id", "name", "email", "phone", "fcmToken", "createdAt",
            "agreed_to_privacy", "agreed_to_terms", "legal_consent_name", 
            "legal_consent_place", "legal_consent_timestamp"
        ]
        
        # Map camelCase to snake_case for core fields if needed
        mapped_data = {}
        mapping = {
            "agreedToPrivacy": "agreed_to_privacy",
            "agreedToTerms": "agreed_to_terms",
            "legalConsentName": "legal_consent_name",
            "legalConsentPlace": "legal_consent_place",
            "legalConsentTimestamp": "legal_consent_timestamp"
        }
        
        for k, v in user_data.items():
            db_key = mapping.get(k, k)
            if db_key in core_fields:
                if db_key == "legal_consent_timestamp" and isinstance(v, str):
                    try:
                        v = datetime.fromisoformat(v)
                    except:
                        v = datetime.utcnow()
                mapped_data[db_key] = v
        
        with cls.get_session() as db:
            # 1. Create Identity
            user = models.User(**mapped_data)
            db.add(user)
            db.flush() # Get ID
            
            # 2. Assign Role
            # Find Role ID
            role_obj = db.query(models.Role).filter(models.Role.name == start_role).first()
            if not role_obj:
                # Fallback or error? For now, create if missing (should be in separate seed)
                import uuid
                role_obj = models.Role(id=str(uuid.uuid4()), name=start_role)
                db.add(role_obj)
                db.flush()
                
            user_role = models.UserRole(user_id=user.id, role_id=role_obj.id, shop_id=None) # shop_id null for initial creation usually?
            db.add(user_role)
            
            # 3. Create Profile
            if start_role == "CUSTOMER":
                profile = models.CustomerProfile(
                    user_id=user.id,
                    profile_photo=profile_photo,
                    # preferences=...
                )
                db.add(profile)
            elif start_role == "OWNER":
                profile = models.OwnerProfile(
                    user_id=user.id,
                    profile_photo=profile_photo,
                    permissions=permissions
                )
                db.add(profile)
            # BARBER handled via Shop logic usually, but we can stub it if needed
            # For now, let the legacy logic or shop implementation handle Staff creation
            
            db.commit()
            
            # Return full object by re-querying
            return cls.get_by_id(user.id)
    
    @classmethod
    def update(cls, user_id: str, update_data: dict):
        """Update user and relevant profile."""
        with cls.get_session() as db:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                return None
                
            # Update Core Identity
            core_fields = [
                "name", "email", "phone", "fcmToken",
                "agreed_to_privacy", "agreed_to_terms", 
                "legal_consent_name", "legal_consent_place", "legal_consent_timestamp"
            ]
            
            mapping = {
                "agreedToPrivacy": "agreed_to_privacy",
                "agreedToTerms": "agreed_to_terms",
                "legalConsentName": "legal_consent_name",
                "legalConsentPlace": "legal_consent_place",
                "legalConsentTimestamp": "legal_consent_timestamp"
            }
            
            for k, v in update_data.items():
                db_key = mapping.get(k, k)
                if db_key in core_fields:
                    if db_key == "legal_consent_timestamp" and isinstance(v, str):
                        try:
                            v = datetime.fromisoformat(v)
                        except:
                            v = datetime.utcnow()
                    setattr(user, db_key, v)
            
            # Update Profiles (Heuristic based on passed fields)
            if "profilePhoto" in update_data:
                # Update ALL profiles attached to this user? Or just the one for the current context?
                # User request was: "Safe to have multiple roles... Role-specific data cleanly separated"
                # So we should probably ONLY update the profile related to the context.
                # BUT, `update_user` is generic.
                # Strategy: Update the profile that matches the user's "primary" role from the perspective of the caller?
                # Simplify: Update CustomerProfile and OwnerProfile if they exist. StaffProfile is usually handled separately.
                
                photo = update_data["profilePhoto"]
                
                # Check for Customer Profile
                cust_profile = db.query(models.CustomerProfile).filter_by(user_id=user.id).first()
                if cust_profile:
                    cust_profile.profile_photo = photo
                    
                # Check for Owner Profile
                own_profile = db.query(models.OwnerProfile).filter_by(user_id=user.id).first()
                if own_profile:
                     own_profile.profile_photo = photo
                     
            if "permissions" in update_data:
                perm = update_data["permissions"]
                own_profile = db.query(models.OwnerProfile).filter_by(user_id=user.id).first()
                if own_profile:
                    own_profile.permissions = perm
                    
            db.commit()
            return cls.get_by_id(user_id)


# Backward-compatible function exports
def get_user_by_email(email: str):
    """Get user by email. (Backward compatible)"""
    return UserRepository.get_by_email(email)


def get_user_by_id(user_id: str):
    """Get user by ID. (Backward compatible)"""
    return UserRepository.get_by_id(user_id)


def get_user_by_phone(phone: str):
    """Get user by phone. (Backward compatible)"""
    return UserRepository.get_by_phone(phone)


def add_user(user_data):
    """Create a new user. (Backward compatible)"""
    return UserRepository.create(user_data)


def update_user(user_id: str, update_data: dict):
    """Update a user. (Backward compatible)"""
    return UserRepository.update(user_id, update_data)
