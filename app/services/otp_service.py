import abc
import os
import random
import string
from typing import Optional

class OTPProvider(abc.ABC):
    @abc.abstractmethod
    def send_otp(self, phone: str, code: str) -> bool:
        """Send OTP to the given phone number."""
        pass

class MockOTPProvider(OTPProvider):
    def send_otp(self, phone: str, code: str) -> bool:
        print(f"========================================")
        print(f" [MOCK OTP] Phone: {phone} | Code: {code}")
        print(f"========================================")
        return True

class TwilioOTPProvider(OTPProvider):
    def __init__(self):
        # account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        # auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        # from_number = os.getenv("TWILIO_FROM_NUMBER")
        # self.client = Client(account_sid, auth_token)
        pass

    def send_otp(self, phone: str, code: str) -> bool:
        # Implement Twilio logic
        return True

class OTPService:
    def __init__(self):
        env = os.getenv("OTP_PROVIDER", "mock")
        if env == "twilio":
            self.provider = TwilioOTPProvider()
        else:
            self.provider = MockOTPProvider()
            
        # In-memory storage for MVP (Use Redis in production)
        self._storage = {} 

    def generate_otp(self) -> str:
        return ''.join(random.choices(string.digits, k=6))

    def request_otp(self, phone: str) -> bool:
        code = "123456" # Fixed for easier testing defaults, or self.generate_otp()
        if os.getenv("ENVIRONMENT") == "production":
            code = self.generate_otp()
            
        # Save to storage (phone -> code)
        self._storage[phone] = code
        
        # Send
        return self.provider.send_otp(phone, code)

    def verify_otp(self, phone: str, code: str) -> bool:
        # In mock mode, allow 123456 always, effectively bypassing storage check
        # This prevents "Invalid OTP" issues if server restarts (clearing memory)
        if os.getenv("OTP_PROVIDER", "mock") == "mock" and code == "123456":
            return True

        if phone not in self._storage:
            return False
        
        stored_code = self._storage[phone]
        # In mock mode, allow 123456 always if configured
        if os.getenv("OTP_PROVIDER") == "mock" and code == "123456":
            return True
            
        if stored_code == code:
            del self._storage[phone] # Burn after reading
            return True
            
        return False

# Singleton instance
otp_service = OTPService()
