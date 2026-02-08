from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from app.routers import base, profile, auth, bookings, shops, reviews, analytics, notifications, uploads, owner, users
from app.services.booking_service import BookingService
from app.services.fcm_service import FCMService

async def run_cleanup():
    last_reset_date = None
    while True:
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Daily Reset Logic (Run once per calendar day)
            if last_reset_date != current_date:
                BookingService.reset_daily_availability()
                last_reset_date = current_date

            count = BookingService.cleanup_expired_bookings()
            if count > 0:
                print(f"🧹 Cleanup: Expired {count} bookings")
            
            # Run operational health checks (e.g., auto-inactivity guard)
            BookingService.run_daily_checks()
            
            # Send appointment reminders
            BookingService.send_appointment_reminders()
        except Exception as e:
            print(f"❌ Cleanup Error: {e}")
        await asyncio.sleep(60) # Run every minute

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Firebase Admin
    FCMService.initialize()
    # Start background cleanup
    cleanup_task = asyncio.create_task(run_cleanup())
    yield
    # Stop background cleanup
    cleanup_task.cancel()

app = FastAPI(title="BarberSync API", lifespan=lifespan)

@app.middleware("http")
async def log_requests(request, call_next):
    import time
    from fastapi import Request
    
    start_time = time.time()
    path = request.url.path
    method = request.method
    
    print(f"\n📥 INCOMING: {method} {path}")
    
    # Try to log body for POST/PUT
    if method in ["POST", "PUT"]:
        try:
            body = await request.body()
            if body:
                print(f"📦 BODY: {body.decode()[:500]}")
        except:
             print("📦 BODY: <unable to read>")

    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    print(f"📤 OUTGOING: {method} {path} - Status: {response.status_code} ({process_time:.2f}ms)")
    
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(shops.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(owner.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(base.router, prefix="/api/v1")

# Serve static files from the uploads directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    return {"message": "Welcome to BarberSync API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
