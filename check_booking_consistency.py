#!/usr/bin/env python3
"""
Database consistency check for booking data visibility issue.
This script verifies that all bookings have valid customer IDs that match user records.
"""
import sys
sys.path.insert(0, '/Users/adityachavhan/Documents/Final_Project/backend')

from app.database.database import SessionLocal
from app.database import models

def check_booking_consistency():
    """Check for bookings with missing or invalid customer IDs."""
    db = SessionLocal()
    try:
        # Query all bookings with LEFT JOIN to users
        results = db.query(models.Booking, models.User).outerjoin(
            models.User, models.Booking.customerId == models.User.id
        ).all()
        
        total_bookings = len(results)
        orphaned_bookings = []
        valid_bookings = []
        
        for booking, user in results:
            if user is None:
                orphaned_bookings.append({
                    'id': booking.id,
                    'customerId': booking.customerId,
                    'date': booking.date,
                    'status': booking.status
                })
            else:
                valid_bookings.append({
                    'id': booking.id,
                    'customerId': booking.customerId,
                    'customerName': user.name,
                    'date': booking.date,
                    'status': booking.status
                })
        
        print("=" * 60)
        print("BOOKING DATABASE CONSISTENCY CHECK")
        print("=" * 60)
        print(f"\n📊 Total Bookings: {total_bookings}")
        print(f"✅ Valid Bookings (with user data): {len(valid_bookings)}")
        print(f"⚠️  Orphaned Bookings (missing user): {len(orphaned_bookings)}")
        
        if orphaned_bookings:
            print("\n" + "=" * 60)
            print("ORPHANED BOOKINGS (NEED ATTENTION)")
            print("=" * 60)
            for booking in orphaned_bookings:
                print(f"\n  Booking ID: {booking['id']}")
                print(f"  Customer ID: {booking['customerId']}")
                print(f"  Date: {booking['date']}")
                print(f"  Status: {booking['status']}")
        
        if valid_bookings:
            print("\n" + "=" * 60)
            print("SAMPLE VALID BOOKINGS (First 5)")
            print("=" * 60)
            for booking in valid_bookings[:5]:
                print(f"\n  Booking ID: {booking['id']}")
                print(f"  Customer: {booking['customerName']} ({booking['customerId']})")
                print(f"  Date: {booking['date']}")
                print(f"  Status: {booking['status']}")
        
        print("\n" + "=" * 60)
        if orphaned_bookings:
            print("⚠️  ACTION REQUIRED: Fix orphaned bookings")
            return False
        else:
            print("✅ All bookings have valid customer references")
            return True
            
    finally:
        db.close()

if __name__ == "__main__":
    success = check_booking_consistency()
    sys.exit(0 if success else 1)
