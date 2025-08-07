from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
import uuid
from datetime import datetime
import PyPDF2
import pdfplumber
import io
import re
import json
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
from docx import Document
import shutil

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# Initialize FastAPI application
app = FastAPI(
    title="ATS Resume Analyzer (Local Mode)",
    description="A comprehensive backend system for ATS resume analysis with local storage",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directories
os.makedirs("local_storage/resumes", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

# In-memory storage (instead of MongoDB/Redis)
resume_analyses = {}
user_sessions = {}

# Pydantic models
class ResumeAnalysisResponse(BaseModel):
    file_id: str
    extracted_text: str
    keywords: List[str]
    skills: List[str]
    experience_years: Optional[int]
    education: List[str]
    ats_score: float
    suggestions: List[str]
    matched_keywords: List[str]
    missing_keywords: List[str]

class JobMatchRequest(BaseModel):
    resume_text: str
    job_description: str

class JobMatchResponse(BaseModel):
    match_percentage: float
    gaps: List[str]
    learning_resources: List[str]
    pass_probability: float

# Resume Analyzer Class
class LocalResumeAnalyzer:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        
        # Common ATS keywords by category
        self.ats_keywords = {
            "technical_skills": [
                "python", "java", "javascript", "react", "angular", "vue", "node.js", "sql", "mongodb",
                "aws", "azure", "docker", "kubernetes", "git", "agile", "scrum", "machine learning",
                "data analysis", "statistics", "excel", "tableau", "power bi", "r", "matlab", "tensorflow",
                "pytorch", "scikit-learn", "pandas", "numpy", "html", "css", "bootstrap", "jquery",
                "typescript", "graphql", "rest api", "microservices", "ci/cd", "jenkins", "gitlab"
            ],
            "soft_skills": [
                "leadership", "communication", "teamwork", "problem solving", "critical thinking",
                "time management", "project management", "customer service", "collaboration",
                "adaptability", "creativity", "analytical", "detail-oriented", "multitasking"
            ],
            "certifications": [
                "pmp", "scrum master", "aws certified", "azure certified", "google cloud",
                "cisco", "comptia", "microsoft certified", "oracle certified", "salesforce"
            ],
            "education": [
                "bachelor", "master", "phd", "degree", "university", "college", "gpa"
            ]
        }

    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file content."""
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
            except Exception as e2:
                print(f"Error extracting PDF text: {e2}")
                return ""

    def extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file content."""
        try:
            doc = Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"Error extracting DOCX text: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'[^\w\s\.\,\!\?\-]', ' ', text)
        return text.lower()

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using NLP."""
        tokens = word_tokenize(self.clean_text(text))
        stop_words = set(stopwords.words('english'))
        tokens = [token for token in tokens if token.lower() not in stop_words and len(token) > 2]
        lemmatized_tokens = [self.lemmatizer.lemmatize(token) for token in tokens]
        return list(set(lemmatized_tokens))

    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text."""
        skills = []
        text_lower = text.lower()
        
        for skill in self.ats_keywords["technical_skills"]:
            if skill in text_lower:
                skills.append(skill)
        
        for skill in self.ats_keywords["soft_skills"]:
            if skill in text_lower:
                skills.append(skill)
        
        return list(set(skills))

    def extract_experience_years(self, text: str) -> Optional[int]:
        """Extract years of experience from text."""
        patterns = [
            r'(\d+)\s*years?\s*of\s*experience',
            r'experience:\s*(\d+)\s*years?',
            r'(\d+)\s*years?\s*in\s*the\s*field'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))
        
        return None

    def extract_education(self, text: str) -> List[str]:
        """Extract education information from text."""
        education = []
        text_lower = text.lower()
        
        degree_patterns = [
            r'bachelor[^s]*s?\s*degree',
            r'master[^s]*s?\s*degree',
            r'ph\.?d\.?',
            r'associate[^s]*s?\s*degree'
        ]
        
        for pattern in degree_patterns:
            if re.search(pattern, text_lower):
                education.append(pattern.replace(r'[^s]*s?\s*degree', 's degree').replace(r'\.?', ''))
        
        return education

    def calculate_ats_score(self, resume_keywords: List[str], job_keywords: List[str]) -> float:
        """Calculate ATS compatibility score."""
        if not job_keywords:
            return 0.0
        
        matched_keywords = set(resume_keywords) & set(job_keywords)
        match_percentage = len(matched_keywords) / len(job_keywords) * 100
        score = min(match_percentage, 100.0)
        
        return round(score, 2)

    def generate_suggestions(self, resume_keywords: List[str], job_keywords: List[str], 
                           missing_keywords: List[str]) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        if missing_keywords:
            suggestions.append(f"Add these keywords to your resume: {', '.join(missing_keywords[:5])}")
        
        if len(resume_keywords) < 20:
            suggestions.append("Consider adding more specific skills and keywords to your resume")
        
        if not any(keyword in resume_keywords for keyword in self.ats_keywords["soft_skills"]):
            suggestions.append("Include soft skills like leadership, communication, and teamwork")
        
        if not any(keyword in resume_keywords for keyword in self.ats_keywords["technical_skills"]):
            suggestions.append("Add technical skills relevant to your target position")
        
        return suggestions

    async def analyze_resume(self, file_content: bytes, filename: str, job_description: str = "") -> Dict[str, Any]:
        """Analyze resume and return comprehensive results."""
        
        # Extract text based on file type
        if filename.lower().endswith('.pdf'):
            text = self.extract_text_from_pdf(file_content)
        elif filename.lower().endswith('.docx'):
            text = self.extract_text_from_docx(file_content)
        else:
            raise ValueError("Unsupported file format. Please upload PDF or DOCX files.")
        
        if not text.strip():
            raise ValueError("Could not extract text from the uploaded file.")
        
        # Extract information
        keywords = self.extract_keywords(text)
        skills = self.extract_skills(text)
        experience_years = self.extract_experience_years(text)
        education = self.extract_education(text)
        
        # Analyze against job description if provided
        job_keywords = []
        matched_keywords = []
        missing_keywords = []
        ats_score = 0.0
        
        if job_description:
            job_keywords = self.extract_keywords(job_description)
            matched_keywords = list(set(keywords) & set(job_keywords))
            missing_keywords = list(set(job_keywords) - set(keywords))
            ats_score = self.calculate_ats_score(keywords, job_keywords)
        
        # Generate suggestions
        suggestions = self.generate_suggestions(keywords, job_keywords, missing_keywords)
        
        # Prepare result
        result = {
            "extracted_text": text,
            "keywords": keywords,
            "skills": skills,
            "experience_years": experience_years,
            "education": education,
            "ats_score": ats_score,
            "suggestions": suggestions,
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        return result

# Initialize analyzer
resume_analyzer = LocalResumeAnalyzer()

# API Routes
@app.post("/api/v1/resume/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume_ats(
    file: UploadFile = File(...),
    job_description: str = Form(""),
    user_id: str = Form("default_user")
):
    """Analyze resume for ATS compatibility."""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx')):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
        
        # Save file locally
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1]
        local_filename = f"local_storage/resumes/{file_id}.{file_extension}"
        
        # Read and save file content
        file_content = await file.read()
        with open(local_filename, "wb") as f:
            f.write(file_content)
        
        # Analyze resume
        analysis_result = await resume_analyzer.analyze_resume(
            file_content, 
            file.filename, 
            job_description
        )
        
        # Store in memory
        resume_analyses[file_id] = {
            "user_id": user_id,
            "filename": file.filename,
            "local_path": local_filename,
            "analysis": analysis_result,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Prepare response
        response = ResumeAnalysisResponse(
            file_id=file_id,
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

@app.post("/api/v1/job/match", response_model=JobMatchResponse)
async def match_resume_to_job(request: JobMatchRequest):
    """Match resume to specific job description."""
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
        for gap in gaps[:5]:
            learning_resources.append(f"Learn {gap}: https://example.com/learn/{gap}")
        
        # Calculate pass probability
        pass_probability = min(match_percentage + 20, 100)
        
        response = JobMatchResponse(
            match_percentage=match_percentage,
            gaps=gaps,
            learning_resources=learning_resources,
            pass_probability=pass_probability
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/resume/history/{user_id}")
async def get_resume_history(user_id: str):
    """Retrieve user's analysis history."""
    try:
        user_resumes = [
            {
                "file_id": file_id,
                "filename": data["filename"],
                "created_at": data["created_at"],
                "ats_score": data["analysis"]["ats_score"]
            }
            for file_id, data in resume_analyses.items()
            if data["user_id"] == user_id
        ]
        
        return {"resumes": user_resumes}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/keywords")
async def get_common_keywords():
    """Get common ATS keywords by category."""
    return {
        "technical_skills": resume_analyzer.ats_keywords["technical_skills"],
        "soft_skills": resume_analyzer.ats_keywords["soft_skills"],
        "certifications": resume_analyzer.ats_keywords["certifications"],
        "education": resume_analyzer.ats_keywords["education"]
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mode": "local",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "storage": "local",
            "database": "memory",
            "cache": "memory"
        }
    }

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "ATS Resume Analyzer API (Local Mode)",
        "version": "2.0.0",
        "mode": "local",
        "documentation": "/docs",
        "redoc": "/redoc"
    } 