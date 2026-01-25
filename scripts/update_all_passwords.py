import sys
import os
import bcrypt

# Add the project root to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.database import SessionLocal
from app.database import models

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def update_passwords():
    db = SessionLocal()
    try:
        new_password = "Pass@123"
        hashed_password = get_password_hash(new_password)
        
        print(f"Updating all users to have password: {new_password}")
        
        users = db.query(models.User).all()
        for user in users:
            user.password = hashed_password
            
        db.commit()
        print(f"Successfully updated passwords for {len(users)} users.")
        
    except Exception as e:
        print(f"Error updating passwords: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_passwords()
