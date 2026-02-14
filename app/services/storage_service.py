import os
import uuid
import shutil
from abc import ABC, abstractmethod
from fastapi import UploadFile
from google.cloud import storage
import logging

logger = logging.getLogger("storage")

class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile) -> str:
        """Upload a file and return its public URL or relative path."""
        pass

class LocalStorageProvider(StorageProvider):
    def __init__(self, upload_dir="uploads"):
        self.upload_dir = upload_dir
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    async def upload(self, file: UploadFile) -> str:
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            return f"/uploads/{unique_filename}"
        except Exception as e:
            logger.error(f"Local upload failed: {e}")
            raise e

class GCSStorageProvider(StorageProvider):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    async def upload(self, file: UploadFile) -> str:
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        blob = self.bucket.blob(unique_filename)
        
        try:
            # Upload from the file-like object directly
            blob.upload_from_file(file.file, content_type=file.content_type)
            # Return the public URL
            return f"https://storage.googleapis.com/{self.bucket_name}/{unique_filename}"
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            raise e

class StorageService:
    def __init__(self):
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        if bucket_name and os.getenv("ENVIRONMENT") == "production":
            logger.info(f"☁️ Storage: Using GCS (bucket: {bucket_name})")
            self.provider = GCSStorageProvider(bucket_name)
        else:
            logger.info("🏠 Storage: Using LOCAL filesystem")
            self.provider = LocalStorageProvider()

    async def upload_file(self, file: UploadFile) -> str:
        return await self.provider.upload(file)

# Singleton instance
storage_service = StorageService()
