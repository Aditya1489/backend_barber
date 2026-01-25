from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.routers import base, profile, auth, bookings, shops, reviews, analytics, notifications, uploads

app = FastAPI(title="BarberSync API")

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
app.include_router(base.router, prefix="/api/v1")

# Serve static files from the uploads directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    return {"message": "Welcome to BarberSync API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
