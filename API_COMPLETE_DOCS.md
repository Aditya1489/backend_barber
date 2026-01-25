# BarberSync API - Complete Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔐 Authentication Endpoints (`/auth`)

### Register
**POST** `/auth/register`
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1 234 567 890",
  "password": "securepassword",
  "role": "CUSTOMER"
}
```

### Login
**POST** `/auth/login`
```json
{
  "email": "john@example.com",
  "password": "securepassword"
}
```

### Google Authentication
**POST** `/auth/google`
```json
{
  "idToken": "google_id_token_here",
  "role": "CUSTOMER"
}
```

### Logout
**POST** `/auth/logout`

### Forgot Password
**POST** `/auth/forgot-password?email=john@example.com`

### Verify Token
**GET** `/auth/verify-token?token=your_token_here`

---

## 👤 Profile Endpoints (`/profile`)

### Get Profile
**GET** `/profile/{user_id}`

### Update Profile
**PUT** `/profile/{user_id}`
```json
{
  "name": "John Doe Updated",
  "phone": "+1 999 888 777",
  "email": "newemail@example.com"
}
```

### Get Permissions
**GET** `/profile/{user_id}/permissions`

### Update Permissions
**PUT** `/profile/{user_id}/permissions`
```json
{
  "location": true,
  "notifications": false,
  "camera": true,
  "storage": true
}
```

### Upload Profile Photo
**POST** `/profile/{user_id}/photo?photo_url=https://example.com/photo.jpg`

---

## 📅 Booking Endpoints (`/bookings`)

### Create Booking
**POST** `/bookings/`
```json
{
  "shopId": "sh1",
  "staffId": "st1",
  "customerId": "user1",
  "services": ["s1", "s2"],
  "date": "2024-02-15",
  "timeSlot": "10:00 AM",
  "notes": "Please use scissors only"
}
```

### Get Bookings (with filters)
**GET** `/bookings/?customer_id=user1&status=PENDING`

Query parameters:
- `customer_id` - Filter by customer
- `staff_id` - Filter by staff
- `shop_id` - Filter by shop
- `status` - Filter by status (PENDING, ACCEPTED, CANCELLED, COMPLETED)

### Get Specific Booking
**GET** `/bookings/{booking_id}`

### Update Booking
**PUT** `/bookings/{booking_id}`
```json
{
  "date": "2024-02-16",
  "timeSlot": "11:00 AM",
  "services": ["s1"],
  "notes": "Updated notes"
}
```

### Update Booking Status
**PATCH** `/bookings/{booking_id}/status?new_status=ACCEPTED`

### Cancel Booking
**DELETE** `/bookings/{booking_id}`

### Get Available Slots
**GET** `/bookings/available-slots/{shop_id}/{staff_id}?date=2024-02-15`

---

## 🏪 Shop Endpoints (`/shops`)

### Get All Shops
**GET** `/shops/?search=barber&lat=40.7128&lng=-74.0060&radius=10`

Query parameters:
- `search` - Search by name or address
- `lat`, `lng` - Location coordinates
- `radius` - Search radius in km

### Get Specific Shop
**GET** `/shops/{shop_id}`

### Create Shop (Owner only)
**POST** `/shops/`
```json
{
  "name": "My Barber Shop",
  "address": "123 Main St, New York, NY",
  "description": "Premium barbering services",
  "coordinates": {"lat": 40.7128, "lng": -74.0060},
  "ownerId": "owner1",
  "phone": "+1 212 555 0100",
  "email": "contact@mybarbershop.com",
  "photos": ["https://example.com/photo1.jpg"],
  "hours": {
    "monday": "9:00 AM - 8:00 PM",
    "tuesday": "9:00 AM - 8:00 PM"
  },
  "amenities": ["WiFi", "Parking"]
}
```

### Update Shop
**PUT** `/shops/{shop_id}`
```json
{
  "name": "Updated Shop Name",
  "phone": "+1 212 555 0200"
}
```

### Delete Shop
**DELETE** `/shops/{shop_id}`

### Get Shop Staff
**GET** `/shops/{shop_id}/staff`

### Add Staff to Shop
**POST** `/shops/{shop_id}/staff/{staff_id}`

### Remove Staff from Shop
**DELETE** `/shops/{shop_id}/staff/{staff_id}`

### Get Shop Services
**GET** `/shops/{shop_id}/services`

### Get Nearby Shops
**GET** `/shops/nearby?lat=40.7128&lng=-74.0060&radius=10`

---

## ⭐ Review Endpoints (`/reviews`)

### Create Review
**POST** `/reviews/`
```json
{
  "shopId": "sh1",
  "customerId": "user1",
  "customerName": "John Doe",
  "rating": 5,
  "comment": "Excellent service!",
  "photos": ["https://example.com/review-photo.jpg"]
}
```

### Get Shop Reviews
**GET** `/reviews/shop/{shop_id}?limit=50&offset=0`

### Get Customer Reviews
**GET** `/reviews/customer/{customer_id}`

### Get Specific Review
**GET** `/reviews/{review_id}`

### Update Review
**PUT** `/reviews/{review_id}`
```json
{
  "rating": 4,
  "comment": "Updated review comment"
}
```

### Delete Review
**DELETE** `/reviews/{review_id}`

### Mark Review as Helpful
**POST** `/reviews/{review_id}/helpful`

### Get Shop Review Statistics
**GET** `/reviews/shop/{shop_id}/stats`

Response:
```json
{
  "shopId": "sh1",
  "totalReviews": 150,
  "averageRating": 4.8,
  "ratingDistribution": {
    "5": 100,
    "4": 30,
    "3": 15,
    "2": 3,
    "1": 2
  }
}
```

---

## 📊 Common Response Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error

---

## 🧪 Testing

### Using curl
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","phone":"+1234567890","password":"test123","role":"CUSTOMER"}'

# Create Booking
curl -X POST http://localhost:8000/api/v1/bookings/ \
  -H "Content-Type: application/json" \
  -d '{"shopId":"sh1","staffId":"st1","customerId":"user1","services":["s1"],"date":"2024-02-15","timeSlot":"10:00 AM"}'

# Get Shops
curl http://localhost:8000/api/v1/shops/

# Create Review
curl -X POST http://localhost:8000/api/v1/reviews/ \
  -H "Content-Type: application/json" \
  -d '{"shopId":"sh1","customerId":"user1","customerName":"John","rating":5,"comment":"Great!"}'
```

---

## 📝 Notes

- All endpoints support CORS
- Mock data is used (replace with database in production)
- Authentication tokens are simplified (use JWT in production)
- File uploads need proper implementation
- Add rate limiting for production
- Implement proper error logging
- Add request validation middleware
