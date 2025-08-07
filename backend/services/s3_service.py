import boto3
import uuid
from typing import Optional
from fastapi import UploadFile
import io
from ..config import settings

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        self.bucket_name = settings.s3_bucket_name

    async def upload_file(self, file: UploadFile) -> str:
        """Upload file to S3 and return the S3 key."""
        file_extension = file.filename.split('.')[-1] if file.filename else 'pdf'
        s3_key = f"resumes/{uuid.uuid4()}.{file_extension}"
        
        # Read file content
        file_content = await file.read()
        
        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type
        )
        
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

    async def get_file_content(self, s3_key: str) -> Optional[bytes]:
        """Get file content from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
        except Exception as e:
            print(f"Error getting file content from S3: {e}")
            return None

s3_service = S3Service() 