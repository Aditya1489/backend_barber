from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.storage_service import storage_service

router = APIRouter(
    prefix="/uploads",
    tags=["uploads"]
)

@router.post("")
async def upload_file(file: UploadFile = File(...)):
    try:
        url = await storage_service.upload_file(file)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
