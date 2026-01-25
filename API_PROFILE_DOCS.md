# Backend API Documentation - Profile Management

## Base URL
```
http://localhost:8000/api/v1
```

## Endpoints

### 1. Get User Profile
**GET** `/profile/{user_id}`

Get complete user profile information including permissions.

**Response:**
```json
{
  "id": "user1",
  "name": "Alex Johnson",
  "email": "alex.johnson@email.com",
  "phone": "+1 234 567 890",
  "role": "CUSTOMER",
  "profilePhoto": "https://picsum.photos/200/200?random=100",
  "permissions": {
    "location": true,
    "notifications": true,
    "camera": true,
    "storage": false
  }
}
```

### 2. Update User Profile
**PUT** `/profile/{user_id}`

Update user profile information (name, email, phone, photo).

**Request Body:**
```json
{
  "name": "Alex Johnson",
  "email": "alex.johnson@email.com",
  "phone": "+1 234 567 890",
  "profilePhoto": "https://example.com/photo.jpg"
}
```

**Note:** All fields are optional. Only send the fields you want to update.

**Response:**
```json
{
  "id": "user1",
  "name": "Alex Johnson",
  "email": "alex.johnson@email.com",
  "phone": "+1 234 567 890",
  "role": "CUSTOMER",
  "profilePhoto": "https://example.com/photo.jpg",
  "permissions": {
    "location": true,
    "notifications": true,
    "camera": true,
    "storage": false
  }
}
```

### 3. Get User Permissions
**GET** `/profile/{user_id}/permissions`

Get only the permissions for a user.

**Response:**
```json
{
  "location": true,
  "notifications": true,
  "camera": true,
  "storage": false
}
```

### 4. Update User Permissions
**PUT** `/profile/{user_id}/permissions`

Update user app permissions.

**Request Body:**
```json
{
  "location": true,
  "notifications": false,
  "camera": true,
  "storage": true
}
```

**Note:** All fields are optional. Only send the permissions you want to update.

**Response:**
```json
{
  "location": true,
  "notifications": false,
  "camera": true,
  "storage": true
}
```

### 5. Upload Profile Photo
**POST** `/profile/{user_id}/photo?photo_url={url}`

Upload or update user profile photo.

**Query Parameters:**
- `photo_url` (string): URL of the uploaded photo

**Response:**
```json
{
  "message": "Profile photo updated successfully",
  "photoUrl": "https://example.com/photo.jpg"
}
```

## Error Responses

### 404 Not Found
```json
{
  "detail": "User not found"
}
```

## Example Usage with curl

### Get Profile
```bash
curl http://localhost:8000/api/v1/profile/user1
```

### Update Profile
```bash
curl -X PUT http://localhost:8000/api/v1/profile/user1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alex Johnson Updated",
    "phone": "+1 999 888 777"
  }'
```

### Update Permissions
```bash
curl -X PUT http://localhost:8000/api/v1/profile/user1/permissions \
  -H "Content-Type: application/json" \
  -d '{
    "location": true,
    "notifications": false
  }'
```

### Upload Photo
```bash
curl -X POST "http://localhost:8000/api/v1/profile/user1/photo?photo_url=https://example.com/new-photo.jpg"
```

## Testing

You can test all endpoints using:
1. **Swagger UI**: http://localhost:8000/docs
2. **ReDoc**: http://localhost:8000/redoc
3. **curl** (examples above)
4. **Postman** or any API client

## Notes

- Currently using mock data (MOCK_USERS dictionary)
- In production, replace with actual database operations
- All endpoints support CORS for frontend integration
- User ID "user1" is available for testing
