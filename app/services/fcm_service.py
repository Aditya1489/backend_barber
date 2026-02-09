import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
from typing import Dict, Any, Optional

class FCMService:
    _initialized = False

    @classmethod
    def initialize(cls):
        """Initialize Firebase Admin SDK"""
        if cls._initialized:
            return
        
        try:
            # 1. Try environment variable (best for Render/Heroku)
            firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS")
            if firebase_creds_json:
                try:
                    creds_dict = json.loads(firebase_creds_json)
                    cred = credentials.Certificate(creds_dict)
                    firebase_admin.initialize_app(cred)
                    cls._initialized = True
                    print("🔥 Firebase Admin initialized via environment variable")
                    return
                except Exception as env_e:
                    print(f"⚠️ Failed to parse FIREBASE_CREDENTIALS env var: {env_e}")

            # 2. Try physical file
            key_path = "serviceAccountKey.json"
            if os.path.exists(key_path):
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                print("🔥 Firebase Admin initialized via serviceAccountKey.json")
            else:
                print("⚠️ Warning: serviceAccountKey.json or FIREBASE_CREDENTIALS env var not found. Push notifications will be disabled.")
        except Exception as e:
            print(f"❌ Firebase Admin initialization failed: {e}")

    @classmethod
    def send_to_user(cls, fcm_token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None):
        """Send a push notification to a specific device token"""
        if not cls._initialized:
            cls.initialize()
            if not cls._initialized:
                return False

        if not fcm_token:
            return False

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
        )

        try:
            response = messaging.send(message)
            print(f"✅ Successfully sent message: {response}")
            return True
        except Exception as e:
            print(f"❌ Error sending FCM message: {e}")
            return False

    @classmethod
    def send_to_topic(cls, topic: str, title: str, body: str, data: Optional[Dict[str, Any]] = None):
        """Send a push notification to all devices subscribed to a topic"""
        if not cls._initialized:
            cls.initialize()
            if not cls._initialized:
                return False

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            topic=topic,
        )

        try:
            response = messaging.send(message)
            print(f"✅ Successfully sent topic message: {response}")
            return True
        except Exception as e:
            print(f"❌ Error sending FCM topic message: {e}")
            return False
