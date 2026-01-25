from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid
import shutil

router = APIRouter(
    prefix="/uploads",
    tags=["uploads"]
)

UPLOAD_DIR = "uploads"

@router.post("")
async def upload_file(file: UploadFile = File(...)):
    # Create directory if it doesn't exist
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    
    # Return the relative path/URL
    return {"url": f"/uploads/{unique_filename}"}
