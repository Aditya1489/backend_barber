from fastapi.testclient import TestClient
from app.main import app
from app.database import models
from app.repositories.user_repository import UserRepository
import uuid

client = TestClient(app)

def test_otp_flow():
    # 1. Customer Flow
    phone = "5555550001" # 10 digits
    
    # Request OTP
    resp = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert resp.status_code == 200
    
    # Verify OTP
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": "123456"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "LOGIN" # Only 1 role (Customer)
    assert "access_token" in data
    user_id = data["user"]["id"]
    print(f"Customer User ID: {user_id}")
    
    # 2. Owner Flow
    owner_phone = "5555550002"
    
    # Register/Login
    client.post("/api/v1/auth/otp/request", json={"phone": owner_phone})
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": owner_phone, "code": "123456"})
    owner_data = resp.json()
    owner_id = owner_data["user"]["id"]
    
    # Create Shop (Simulate "Become a Partner")
    shop_data = {
        "name": "Test Barbershop",
        "address": "123 Test St",
        "description": "Best cuts",
        "coordinates": {"lat": 0, "lng": 0},
        "ownerId": owner_id,
        "phone": "555555SHOP",
        "email": "shop@test.com"
    }
    resp = client.post("/api/v1/shops/", json=shop_data)
    assert resp.status_code == 201
    shop_id = resp.json()["id"]
    print(f"Shop Created: {shop_id}")
    
    # Login again to see Updated Roles
    client.post("/api/v1/auth/otp/request", json={"phone": owner_phone})
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": owner_phone, "code": "123456"})
    data = resp.json()
    # Now should have OWNER role
    assert data["action"] == "SELECT_ROLE"
    roles = data["roles"]
    assert len(roles) >= 2 # Customer + Owner
    
    # Select Owner Role
    resp = client.post("/api/v1/auth/login/select-role", json={
        "user_id": owner_id,
        "role": "OWNER",
        "shop_id": shop_id
    })
    assert resp.status_code == 200
    owner_token = resp.json()["access_token"]
    
    # 3. Invite Flow
    staff_phone = "5555550003"
    
    # Create Invite (As Owner)
    resp = client.post("/api/v1/invites/", 
        json={"phone": staff_phone, "shop_id": shop_id, "role": "BARBER"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 200
    invite_id = resp.json()["id"]
    
    # Login as Staff
    client.post("/api/v1/auth/otp/request", json={"phone": staff_phone})
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": staff_phone, "code": "123456"})
    staff_login_data = resp.json()
    staff_id = staff_login_data["user"]["id"]
    
    if staff_login_data.get("action") == "SELECT_ROLE":
        # Select CUSTOMER role to see invites
        resp = client.post("/api/v1/auth/login/select-role", json={
            "user_id": staff_id,
            "role": "CUSTOMER"
        })
        staff_token = resp.json()["access_token"]
    else:
        staff_token = staff_login_data["access_token"] 
    
    # Check Invites
    resp = client.get("/api/v1/invites/my", headers={"Authorization": f"Bearer {staff_token}"})
    assert resp.status_code == 200
    my_invites = resp.json()
    assert len(my_invites) > 0
    # Check if our invite is present (handling potential old data)
    found = any(i["id"] == invite_id for i in my_invites)
    assert found, f"Invite {invite_id} not found in {my_invites}"
    
    # Accept Invite
    resp = client.post(f"/api/v1/invites/{invite_id}/accept", 
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert resp.status_code == 200
    
    # Login Staff (Customer Role initially)
    client.post("/api/v1/auth/otp/request", json={"phone": staff_phone})
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": staff_phone, "code": "123456"})
    data = resp.json()
    staff_token = data.get("access_token")
    client.headers["Authorization"] = f"Bearer {staff_token}"
    assert data["action"] == "SELECT_ROLE"
    roles = [r["role"] for r in data["roles"]]
    assert "BARBER" in roles
    
    print("ALL TESTS PASSED")
    

if __name__ == "__main__":
    test_otp_flow()
