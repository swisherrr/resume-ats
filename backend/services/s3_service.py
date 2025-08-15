import boto3
import uuid
import os
from typing import Optional
from fastapi import UploadFile
import io
from pathlib import Path
from ..config import settings

class S3Service:
    def __init__(self):
        # Check if AWS credentials are configured
        if not settings.aws_access_key_id or not settings.aws_secret_access_key:
            print("Warning: AWS credentials not configured. Using local file storage as fallback.")
            self.s3_client = None
            self.bucket_name = None
            self.use_local_storage = True
        else:
            print(f"Using S3 storage with bucket: {settings.s3_bucket_name}")
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
            self.bucket_name = settings.s3_bucket_name
            self.use_local_storage = False
        
        # Create local upload directory for fallback
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)

    async def upload_file(self, file: UploadFile) -> str:
        """Upload file to S3 or local storage and return the key/path."""
        file_extension = file.filename.split('.')[-1] if file.filename else 'pdf'
        file_id = str(uuid.uuid4())
        
        # Read file content
        file_content = await file.read()
        
        if self.use_local_storage:
            # Save to local storage
            file_path = self.upload_dir / f"{file_id}.{file_extension}"
            with open(file_path, "wb") as f:
                f.write(file_content)
            print(f"File saved locally to: {file_path}")
            return str(file_path)
        else:
            # Upload to S3
            s3_key = f"resumes/{file_id}.{file_extension}"
            print(f"Uploading to S3 bucket '{self.bucket_name}' with key: {s3_key}")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=file.content_type
            )
            print(f"File successfully uploaded to S3: s3://{self.bucket_name}/{s3_key}")
            return s3_key

    async def get_file_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for file access."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            return ""

    async def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except Exception as e:
            print(f"Error deleting file from S3: {e}")
            return False

    async def get_file_content(self, file_key: str) -> Optional[bytes]:
        """Get file content from S3 or local storage."""
        try:
            if self.use_local_storage:
                # Read from local storage
                with open(file_key, "rb") as f:
                    return f.read()
            else:
                # Read from S3
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                return response['Body'].read()
        except Exception as e:
            print(f"Error getting file content: {e}")
            return None

s3_service = S3Service() 