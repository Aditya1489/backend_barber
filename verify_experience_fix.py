
import requests
import sys

# Base URL - adjusting for terminal execution
BASE_URL = "http://localhost:8000/api/v1"

def test_experience_update():
    # 1. Get a staff ID to test with
    print("Fetching shops to find a staff member...")
    response = requests.get(f"{BASE_URL}/shops")
    if response.status_code != 200:
        print("Failed to fetch shops")
        return
    
    shops = response.json()
    if not shops:
        print("No shops found")
        return
    
    staff_id = None
    for shop in shops:
        if shop.get("staff"):
            staff_id = shop["staff"][0]["id"]
            break
    
    if not staff_id:
        print("No staff member found in any shop")
        return
    
    print(f"Testing with staff_id: {staff_id}")
    
    # 2. Get current profile
    print("Getting current profile...")
    response = requests.get(f"{BASE_URL}/shops/staff/{staff_id}/profile")
    profile = response.json()
    original_exp = profile.get("experience", 0)
    print(f"Original experience: {original_exp}")
    
    # 3. Update experience to a new value (e.g. 10)
    new_exp = 10 if original_exp != 10 else 5
    print(f"Updating experience to {new_exp}...")
    update_response = requests.put(f"{BASE_URL}/shops/staff/{staff_id}/profile", json={
        "experience": new_exp,
        "name": profile.get("name"),
        "phone": profile.get("phone")
    })
    if update_response.status_code != 200:
        print(f"Update failed: {update_response.text}")
        return
    
    # 4. Verify update
    print("Verifying first update...")
    response = requests.get(f"{BASE_URL}/shops/staff/{staff_id}/profile")
    profile = response.json()
    if profile.get("experience") == new_exp:
        print(f"✅ Second update verified: experience is {new_exp}")
    else:
        print(f"❌ Verification failed: expected {new_exp}, got {profile.get('experience')}")
        return

    # 5. Update experience to 0
    print("Updating experience to 0...")
    update_response = requests.put(f"{BASE_URL}/shops/staff/{staff_id}/profile", json={
        "experience": 0,
        "name": profile.get("name")
    })
    
    # 6. Verify 0 update
    print("Verifying 0 update...")
    response = requests.get(f"{BASE_URL}/shops/staff/{staff_id}/profile")
    profile = response.json()
    if profile.get("experience") == 0:
        print("✅ SUCCESS: Experience 0 correctly persisted and retrieved!")
    else:
        print(f"❌ FAILURE: Expected experience 0, but got {profile.get('experience')}")

if __name__ == "__main__":
    test_experience_update()
