from datetime import datetime
from app.database.database import SessionLocal
from app.database import models
from app.repositories.booking_repository import BookingRepository
from app.repositories import NotificationRepository
from app.services.fcm_service import FCMService
import logging

logger = logging.getLogger(__name__)

class BookingService:
    @staticmethod
    def cleanup_expired_bookings():
        """Find and mark bookings that past their expiry time as EXPIRED."""
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            expired_bookings = db.query(models.Booking).filter(
                models.Booking.status == "AWAITING_CUSTOMER_CONFIRMATION",
                models.Booking.expiresAt != None,
                models.Booking.expiresAt < now
            ).all()

            for booking in expired_bookings:
                logger.info(f"Expiring booking {booking.id} - TTL reached.")
                booking.status = "EXPIRED"
                
                # Notify customer
                NotificationRepository.create(
                    user_id=booking.customerId,
                    title="Booking Expired",
                    body="Your booking request has expired because the confirmation fee was not paid in time.",
                    notif_type="APPOINTMENT",
                    data={"booking_id": booking.id}
                )
                
                # Notify barber
                staff = db.query(models.Staff).filter(models.Staff.id == booking.staffId).first()
                if staff:
                    NotificationRepository.create(
                        user_id=staff.userId,
                        title="Booking Slot Released",
                        body=f"Slot {booking.timeSlot} on {booking.date} has been released due to unpaid confirmation.",
                        notif_type="APPOINTMENT",
                        data={"booking_id": booking.id}
                    )
                    # Push Notification
                    staff_user = db.query(models.User).filter(models.User.id == staff.userId).first()
                    if staff_user and staff_user.fcmToken:
                        FCMService.send_to_user(
                            fcm_token=staff_user.fcmToken,
                            title="Booking Slot Released 🕊️",
                            body=f"Slot {booking.timeSlot} on {booking.date} is now available.",
                            data={"bookingId": booking.id, "type": "SLOT_RELEASED"}
                        )
                
                # Push Notification to customer (NEW)
                customer_user = db.query(models.User).filter(models.User.id == booking.customerId).first()
                if customer_user and customer_user.fcmToken:
                    FCMService.send_to_user(
                        fcm_token=customer_user.fcmToken,
                        title="Booking Expired ❌",
                        body="Your booking has expired due to non-payment of the confirmation fee.",
                        data={"bookingId": booking.id, "type": "BOOKING_EXPIRED"}
                    )
            
            db.commit()
            return len(expired_bookings)
        except Exception as e:
            logger.error(f"Error in cleanup_expired_bookings: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    @staticmethod
    def run_daily_checks():
        """Perform daily operational health checks."""
        db = SessionLocal()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            # 1. Auto-Inactivity Guard
            # If a barber's first booking of the day is NO_SHOW, they might be inactive.
            # Alert owner and potentially toggle availability.
            no_shows = db.query(models.Booking).filter(
                models.Booking.date == today,
                models.Booking.status == "NO_SHOW"
            ).all()
            
            for booking in no_shows:
                # Check if this was their first one
                earlier_bookings = db.query(models.Booking).filter(
                    models.Booking.staffId == booking.staffId,
                    models.Booking.date == today,
                    models.Booking.timeSlot < booking.timeSlot
                ).count()
                
                if earlier_bookings == 0:
                    # First booking of the day was a NO_SHOW!
                    staff = db.query(models.Staff).filter(models.Staff.id == booking.staffId).first()
                    if staff and staff.isAvailable:
                        logger.warning(f"Staff {staff.name} missed first booking. Marking as unavailable.")
                        staff.isAvailable = False
                        
                        # Notify Owner
                        shop = db.query(models.Shop).filter(models.Shop.id == staff.shopId).first()
                        if shop:
                            NotificationRepository.create(
                                user_id=shop.ownerId,
                                title=f"Staff Alert: {staff.name}",
                                body=f"{staff.name} missed their first appointment today. They have been marked as UNAVAILABLE for now.",
                                notif_type="SYSTEM",
                                data={"staff_id": staff.id}
                            )
            db.commit()
        except Exception as e:
            logger.error(f"Error in operational checks: {e}")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def aggregate_monthly_fees():
        """Aggregate monthly revenue and calculate 20% platform fee per shop."""
        db = SessionLocal()
        try:
            from datetime import timedelta
            # Calculate for the previous month (simplified: last 30 days)
            start_date = datetime.now() - timedelta(days=30)
            
            # Group by shop
            shops = db.query(models.Shop).all()
            for shop in shops:
                monthly_bookings = db.query(models.Booking).filter(
                    models.Booking.shopId == shop.id,
                    models.Booking.status == "COMPLETED",
                    models.Booking.bookedAt >= start_date
                ).all()
                
                total_revenue = sum(b.totalAmount for b in monthly_bookings)
                platform_fee = total_revenue * 0.20
                
                if total_revenue > 0:
                    logger.info(f"Shop {shop.name} | Revenue: {total_revenue} | Fee: {platform_fee}")
                    from app.repositories import NotificationRepository
                    NotificationRepository.create(
                        user_id=shop.ownerId,
                        title="Monthly Revenue Summary",
                        body=f"Your shop earned {total_revenue} this month. The platform fee (20%) is {platform_fee}. An invoice has been generated.",
                        notif_type="SYSTEM",
                        data={"revenue": total_revenue, "fee": platform_fee}
                    )
            
            db.commit()
        except Exception as e:
            logger.error(f"Error aggregating monthly fees: {e}")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def reset_daily_availability():
        """Reset all staff to available at the start of a new day."""
        db = SessionLocal()
        try:
            db.query(models.Staff).update({models.Staff.isAvailable: True})
            db.commit()
            logger.info("Daily availability reset completed for all staff.")
        except Exception as e:
            logger.error(f"Error resetting daily availability: {e}")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def send_appointment_reminders():
        """Send reminders for upcoming confirmed appointments."""
        db = SessionLocal()
        try:
            from datetime import timedelta
            now = datetime.utcnow()
            
            # Fetch confirmed bookings
            upcoming = db.query(models.Booking).filter(
                models.Booking.status == "CONFIRMED"
            ).all()

            for b in upcoming:
                try:
                    # Parse booking time (assumes 'YYYY-MM-DD' and 'HH:MM AM/PM')
                    b_datetime = datetime.strptime(f"{b.date} {b.timeSlot}", "%Y-%m-%d %I:%M %p")
                    diff = b_datetime - now

                    # 24 Hour Reminder
                    if timedelta(hours=23) < diff <= timedelta(hours=24) and not b.reminded24h:
                        NotificationRepository.create(
                            user_id=b.customerId,
                            title="Appointment Tomorrow 📅",
                            body=f"Reminder: You have a haircut scheduled tomorrow at {b.timeSlot}.",
                            notif_type="APPOINTMENT",
                            data={"booking_id": b.id}
                        )
                        b.reminded24h = True

                    # 2 Hour Reminder
                    elif timedelta(hours=1.5) < diff <= timedelta(hours=2) and not b.reminded2h:
                        NotificationRepository.create(
                            user_id=b.customerId,
                            title="Appointment in 2 Hours! 💈",
                            body=f"Get ready! Your appointment at {b.timeSlot} is in just 2 hours.",
                            notif_type="APPOINTMENT",
                            data={"booking_id": b.id}
                        )
                        b.reminded2h = True

                    # 15 Minute Reminder
                    elif timedelta(minutes=10) < diff <= timedelta(minutes=15) and not b.reminded15m:
                        NotificationRepository.create(
                            user_id=b.customerId,
                            title="Almost Time! 🕒",
                            body="Your barber is waiting. Your appointment starts in 15 minutes.",
                            notif_type="APPOINTMENT",
                            data={"booking_id": b.id}
                        )
                        b.reminded15m = True
                    
                    # Send FCM Push for all reminders (if token exists)
                    customer_user = db.query(models.User).filter(models.User.id == b.customerId).first()
                    if customer_user and customer_user.fcmToken:
                        rem_title = ""
                        rem_body = ""
                        if b.reminded24h and (timedelta(hours=23) < diff <= timedelta(hours=24)):
                            rem_title = "Appointment Tomorrow 📅"
                            rem_body = f"Reminder: You have a haircut scheduled tomorrow at {b.timeSlot}."
                        elif b.reminded2h and (timedelta(hours=1.5) < diff <= timedelta(hours=2)):
                            rem_title = "Appointment in 2 Hours! 💈"
                            rem_body = f"Get ready! Your appointment at {b.timeSlot} is in just 2 hours."
                        elif b.reminded15m and (timedelta(minutes=10) < diff <= timedelta(minutes=15)):
                            rem_title = "Almost Time! 🕒"
                            rem_body = "Your barber is waiting. Your appointment starts in 15 minutes."

                        if rem_title:
                            FCMService.send_to_user(
                                fcm_token=customer_user.fcmToken,
                                title=rem_title,
                                body=rem_body,
                                data={"bookingId": b.id, "type": "REMINDER"}
                            )
                        
                except Exception as e:
                    logger.error(f"Error parsing date for booking {b.id}: {e}")
            
            db.commit()
        except Exception as e:
            logger.error(f"Error in send_appointment_reminders: {e}")
            db.rollback()
        finally:
            db.close()
