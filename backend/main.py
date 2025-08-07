from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

# Import our modules
from .config import settings
from .database import connect_to_mongo, close_mongo_connection, get_database
from .models import ResumeModel, JobPostingModel, SkillsTaxonomyModel, ResumeAnalysisRequest, ResumeAnalysisResponse, JobMatchRequest, JobMatchResponse
from .services.s3_service import s3_service
from .services.resume_analyzer import ResumeAnalyzer

# Initialize FastAPI application
app = FastAPI(
    title=settings.project_name,
    description="A comprehensive backend system for ATS resume analysis with keyword matching, scoring, and optimization",
    version=settings.version
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable for resume analyzer
resume_analyzer = None

@app.on_event("startup")
async def startup_event():
    """Initialize database connections and services."""
    await connect_to_mongo()
    
    # Initialize resume analyzer
    global resume_analyzer
    resume_analyzer = ResumeAnalyzer(get_database())

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections."""
    await close_mongo_connection()

# API Routes

@app.post(f"{settings.api_v1_prefix}/resume/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume_ats(
    file: UploadFile = File(...),
    job_description: str = Form(""),
    user_id: str = Form("default_user")
):
    """
    Analyze resume for ATS compatibility.
    
    Upload a PDF or DOCX resume and optionally provide a job description
    to receive comprehensive ATS compatibility scoring with actionable
    improvement suggestions.
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx')):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
        
        # Upload file to S3
        s3_key = await s3_service.upload_file(file)
        
        # Get file content for analysis
        file_content = await s3_service.get_file_content(s3_key)
        if not file_content:
            raise HTTPException(status_code=500, detail="Failed to retrieve file content")
        
        # Analyze resume
        analysis_result = await resume_analyzer.analyze_resume(
            file_content, 
            file.filename, 
            job_description
        )
        
        # Store in MongoDB
        resume_data = ResumeModel(
            user_id=user_id,
            filename=file.filename,
            s3_key=s3_key,
            parsed_content=analysis_result,
            analysis_results=analysis_result
        )
        
        db = get_database()
        result = await db.resumes.insert_one(resume_data.dict(by_alias=True))
        
        # Prepare response
        response = ResumeAnalysisResponse(
            file_id=str(result.inserted_id),
            extracted_text=analysis_result["extracted_text"],
            keywords=analysis_result["keywords"],
            skills=analysis_result["skills"],
            experience_years=analysis_result["experience_years"],
            education=analysis_result["education"],
            ats_score=analysis_result["ats_score"],
            suggestions=analysis_result["suggestions"],
            matched_keywords=analysis_result["matched_keywords"],
            missing_keywords=analysis_result["missing_keywords"]
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{settings.api_v1_prefix}/job/match", response_model=JobMatchResponse)
async def match_resume_to_job(request: JobMatchRequest):
    """
    Match resume to specific job description.
    
    Submit both resume text and target job description to receive
    compatibility analysis, pass probability, and targeted improvement
    recommendations.
    """
    try:
        # Analyze resume against job description
        analysis_result = await resume_analyzer.analyze_resume(
            request.resume_text.encode(), 
            "resume.txt", 
            request.job_description
        )
        
        # Calculate match percentage and gaps
        match_percentage = analysis_result["ats_score"]
        gaps = analysis_result["missing_keywords"]
        
        # Generate learning resources for gaps
        learning_resources = []
        for gap in gaps[:5]:  # Top 5 gaps
            learning_resources.append(f"Learn {gap}: https://example.com/learn/{gap}")
        
        # Calculate pass probability (simplified)
        pass_probability = min(match_percentage + 20, 100)  # Add 20% buffer
        
        response = JobMatchResponse(
            match_percentage=match_percentage,
            gaps=gaps,
            learning_resources=learning_resources,
            pass_probability=pass_probability
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_v1_prefix}/resume/history/{{user_id}}")
async def get_resume_history(user_id: str):
    """
    Retrieve user's analysis history.
    
    Returns previous analyses with timestamps for the specified user.
    """
    try:
        db = get_database()
        cursor = db.resumes.find({"user_id": user_id}).sort("created_at", -1)
        resumes = await cursor.to_list(length=50)
        
        # Convert ObjectId to string for JSON serialization
        for resume in resumes:
            resume["_id"] = str(resume["_id"])
            resume["created_at"] = resume["created_at"].isoformat()
            resume["updated_at"] = resume["updated_at"].isoformat()
        
        return {"resumes": resumes}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_v1_prefix}/resume/{{file_id}}")
async def get_resume_analysis(file_id: str):
    """
    Get specific resume analysis by file ID.
    """
    try:
        db = get_database()
        resume = await db.resumes.find_one({"_id": file_id})
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume analysis not found")
        
        # Convert ObjectId to string
        resume["_id"] = str(resume["_id"])
        resume["created_at"] = resume["created_at"].isoformat()
        resume["updated_at"] = resume["updated_at"].isoformat()
        
        return resume
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_v1_prefix}/keywords")
async def get_common_keywords():
    """
    Get common ATS keywords by category.
    """
    return {
        "technical_skills": resume_analyzer.ats_keywords["technical_skills"],
        "soft_skills": resume_analyzer.ats_keywords["soft_skills"],
        "certifications": resume_analyzer.ats_keywords["certifications"],
        "education": resume_analyzer.ats_keywords["education"]
    }

@app.get(f"{settings.api_v1_prefix}/health")
async def health_check():
    """
    Health check endpoint.
    """
    try:
        # Check MongoDB connection
        db = get_database()
        await db.command("ping")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "mongodb": "connected"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Root endpoint for API documentation
@app.get("/")
async def root():
    """
    API root endpoint with documentation links.
    """
    return {
        "message": "ATS Resume Analyzer API",
        "version": settings.version,
        "documentation": "/docs",
        "redoc": "/redoc"
    } 