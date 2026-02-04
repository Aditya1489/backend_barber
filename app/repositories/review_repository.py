"""
Review repository - handles all review-related database operations.
"""
import uuid
from app.repositories.base import BaseRepository
from app.database.database import SessionLocal
from app.database import models


class ReviewRepository(BaseRepository):
    """Repository for Review entity operations."""
    
    @classmethod
    def create(cls, review_data: dict):
        """Create a new review and update shop/staff ratings."""
        db = SessionLocal()
        try:
            new_review = models.Review(
                id=str(uuid.uuid4()),
                shopId=review_data["shopId"],
                staffId=review_data.get("staffId"),
                customerId=review_data["customerId"],
                customerName=review_data["customerName"],
                rating=review_data["rating"],
                comment=review_data.get("comment", ""),
                photos=review_data.get("photos", []),
                helpful=0
            )
            db.add(new_review)
            db.flush()
            
            # Rating aggregation
            try:
                shop_id = review_data["shopId"]
                staff_id = review_data.get("staffId")
                
                # Update Shop rating
                shop_reviews = db.query(models.Review).filter(models.Review.shopId == shop_id).all()
                if shop_reviews:
                    shop = db.query(models.Shop).filter(models.Shop.id == shop_id).first()
                    if shop:
                        avg_rating = sum(r.rating for r in shop_reviews) / len(shop_reviews)
                        shop.rating = round(avg_rating, 1)
                        shop.reviewsCount = len(shop_reviews)
                
                # Update Staff rating
                if staff_id:
                    staff_id_str = str(staff_id)
                    staff_reviews = db.query(models.Review).filter(models.Review.staffId == staff_id_str).all()
                    if staff_reviews:
                        staff = db.query(models.Staff).filter(models.Staff.id == staff_id_str).first()
                        if staff:
                            avg_rating = sum(r.rating for r in staff_reviews) / len(staff_reviews)
                            staff.rating = round(avg_rating, 1)
                            staff.reviewsCount = len(staff_reviews)
            except Exception:
                pass  # Don't fail review creation if aggregation fails
                
            db.commit()
            db.refresh(new_review)
            
            return {
                "id": new_review.id,
                "shopId": new_review.shopId,
                "staffId": str(new_review.staffId) if new_review.staffId else None,
                "customerId": new_review.customerId,
                "customerName": new_review.customerName,
                "rating": new_review.rating,
                "comment": new_review.comment,
                "photos": new_review.photos,
                "createdAt": new_review.createdAt.isoformat() + "Z",
                "helpful": new_review.helpful
            }
        finally:
            db.close()
    
    @classmethod
    def get_all(cls, shop_id=None, customer_id=None, staff_id=None):
        """Get reviews with optional filters."""
        db = SessionLocal()
        try:
            query = db.query(models.Review)
            if shop_id:
                query = query.filter(models.Review.shopId == shop_id)
            if customer_id:
                query = query.filter(models.Review.customerId == customer_id)
            if staff_id:
                query = query.filter(models.Review.staffId == staff_id)
            
            reviews = query.order_by(models.Review.createdAt.desc()).all()
            return [{
                "id": r.id,
                "shopId": r.shopId,
                "staffId": str(r.staffId) if r.staffId else None,
                "customerId": r.customerId,
                "customerName": r.customerName,
                "rating": r.rating,
                "comment": r.comment,
                "photos": r.photos,
                "createdAt": r.createdAt.isoformat() + "Z",
                "helpful": r.helpful
            } for r in reviews]
        finally:
            db.close()
    
    @classmethod
    def update(cls, review_id: str, update_data: dict):
        """Update a review."""
        db = SessionLocal()
        try:
            review = db.query(models.Review).filter(models.Review.id == review_id).first()
            if not review:
                return None
            
            for key, value in update_data.items():
                if hasattr(review, key):
                    setattr(review, key, value)
            
            db.commit()
            db.refresh(review)
            return {
                "id": review.id,
                "shopId": review.shopId,
                "customerId": review.customerId,
                "customerName": review.customerName,
                "rating": review.rating,
                "comment": review.comment,
                "photos": review.photos,
                "createdAt": review.createdAt.isoformat() + "Z",
                "helpful": review.helpful
            }
        finally:
            db.close()
    
    @classmethod
    def delete(cls, review_id: str):
        """Delete a review."""
        db = SessionLocal()
        try:
            review = db.query(models.Review).filter(models.Review.id == review_id).first()
            if not review:
                return False
            db.delete(review)
            db.commit()
            return True
        finally:
            db.close()


# Backward-compatible function exports
def create_review(review_data: dict):
    """Create a new review. (Backward compatible)"""
    return ReviewRepository.create(review_data)


def get_reviews(shop_id=None, customer_id=None, staff_id=None):
    """Get reviews with filters. (Backward compatible)"""
    return ReviewRepository.get_all(shop_id, customer_id, staff_id)


def update_review(review_id: str, update_data: dict):
    """Update a review. (Backward compatible)"""
    return ReviewRepository.update(review_id, update_data)


def delete_review(review_id: str):
    """Delete a review. (Backward compatible)"""
    return ReviewRepository.delete(review_id)
