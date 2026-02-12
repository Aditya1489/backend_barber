from app.repositories.base import BaseRepository
from app.database import models
from datetime import datetime, timedelta

class InviteRepository(BaseRepository):
    @classmethod
    def _to_dict(cls, invite):
        if not invite: return None
        return {
            "id": invite.id,
            "phone": invite.phone,
            "shop_id": invite.shop_id,
            "role": invite.role,
            "status": invite.status,
            "expires_at": invite.expires_at,
            "created_at": invite.created_at
        }

    @classmethod
    def create(cls, shop_id: str, phone: str, role: str = "BARBER"):
        with cls.get_session() as db:
            # Check active invites
            existing = db.query(models.StaffInvite).filter(
                models.StaffInvite.shop_id == shop_id,
                models.StaffInvite.phone == phone,
                models.StaffInvite.status == "PENDING"
            ).first()
            
            if existing:
                return cls._to_dict(existing)
                
            invite = models.StaffInvite(
                shop_id=shop_id,
                phone=phone,
                role=role,
                status="PENDING",
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.add(invite)
            db.commit()
            db.refresh(invite)
            return cls._to_dict(invite)

    @classmethod
    def get_pending_by_phone(cls, phone: str):
        with cls.get_session() as db:
            invites = db.query(models.StaffInvite).filter(
                models.StaffInvite.phone == phone,
                models.StaffInvite.status == "PENDING",
                models.StaffInvite.expires_at > datetime.utcnow()
            ).all()
            return [cls._to_dict(i) for i in invites]

    @classmethod
    def get_by_id(cls, invite_id: str):
        with cls.get_session() as db:
            invite = db.query(models.StaffInvite).filter(models.StaffInvite.id == invite_id).first()
            return cls._to_dict(invite)

    @classmethod
    def accept_invite(cls, invite_id: str):
         with cls.get_session() as db:
            invite = db.query(models.StaffInvite).filter(models.StaffInvite.id == invite_id).first()
            if invite:
                invite.status = "ACCEPTED"
                db.commit()
                db.refresh(invite)
                return cls._to_dict(invite)
            return None
