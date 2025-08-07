import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "ats_resume_analyzer"
    
    # Redis Configuration (optional, for backward compatibility)
    redis_url: Optional[str] = None
    
    # AWS Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "ats-resume-uploads"
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    project_name: str = "ATS Resume Analyzer"
    version: str = "2.0.0"
    
    # Security
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings() 