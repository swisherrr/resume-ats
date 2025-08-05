from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse
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
import requests

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('tokenizers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger')

# Initialize basic text processing
nlp = None

# Initialize FastAPI application with metadata
app = FastAPI(
    title="ATS Resume Analyzer",
    description="A comprehensive backend system for ATS resume analysis with keyword matching, scoring, and optimization",
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

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

# Pydantic models for request/response
class JobDescription(BaseModel):
    title: str
    description: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []

class ResumeAnalysis(BaseModel):
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

class ATSOptimizationRequest(BaseModel):
    resume_text: str
    job_description: str
    target_keywords: List[str] = []

# Global variables for storing analysis results
resume_analyses = {}

# Common ATS keywords by category
ATS_KEYWORDS = {
    "technical_skills": [
        "python", "java", "javascript", "react", "angular", "vue", "node.js", "sql", "mongodb",
        "aws", "azure", "docker", "kubernetes", "git", "agile", "scrum", "machine learning",
        "data analysis", "statistics", "excel", "powerbi", "tableau", "html", "css", "php"
    ],
    "soft_skills": [
        "leadership", "communication", "teamwork", "problem solving", "critical thinking",
        "time management", "organization", "adaptability", "creativity", "collaboration"
    ],
    "certifications": [
        "pmp", "scrum master", "aws certified", "microsoft certified", "google certified",
        "cisco certified", "comptia", "itil", "six sigma", "lean"
    ],
    "education": [
        "bachelor", "master", "phd", "degree", "university", "college", "certification"
    ]
}

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using multiple methods for better accuracy."""
    text = ""
    
    # Method 1: Try pdfplumber (better for complex layouts)
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"pdfplumber failed: {e}")
    
    # Method 2: Fallback to PyPDF2
    if not text.strip():
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"PyPDF2 failed: {e}")
    
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from Word document."""
    try:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""

def clean_text(text: str) -> str:
    """Clean and normalize text for analysis."""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    text = text.lower()
    
    # Remove special characters but keep important ones
    text = re.sub(r'[^\w\s\-\.\,\!\?]', ' ', text)
    
    return text.strip()

def extract_keywords(text: str) -> List[str]:
    """Extract relevant keywords from text."""
    # Clean text
    cleaned_text = clean_text(text)
    
    # Tokenize
    tokens = word_tokenize(cleaned_text)
    
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token.lower() not in stop_words and len(token) > 2]
    
    # Lemmatize
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(token) for token in tokens]
    
    # Filter for relevant keywords
    all_keywords = []
    for category, keywords in ATS_KEYWORDS.items():
        all_keywords.extend(keywords)
    
    # Find matches
    found_keywords = []
    for token in tokens:
        if token.lower() in [kw.lower() for kw in all_keywords]:
            found_keywords.append(token.lower())
    
    return list(set(found_keywords))

def extract_skills(text: str) -> List[str]:
    """Extract skills from resume text."""
    skills = []
    
    # Common skill patterns
    skill_patterns = [
        r'\b(?:proficient in|skilled in|experience with|knowledge of)\s+([^\.]+)',
        r'\b(?:python|java|javascript|react|angular|vue|node\.js|sql|mongodb|aws|azure|docker|kubernetes|git)\b',
        r'\b(?:leadership|communication|teamwork|problem solving|critical thinking|time management)\b'
    ]
    
    for pattern in skill_patterns:
        matches = re.findall(pattern, text.lower())
        skills.extend(matches)
    
    # Also use keyword extraction
    keywords = extract_keywords(text)
    skills.extend(keywords)
    
    return list(set(skills))

def extract_experience_years(text: str) -> Optional[int]:
    """Extract years of experience from resume."""
    # Look for patterns like "X years of experience" or "X+ years"
    patterns = [
        r'(\d+)\s*(?:years?|yrs?)\s*(?:of\s*)?experience',
        r'(\d+)\+\s*(?:years?|yrs?)\s*(?:of\s*)?experience',
        r'experience:\s*(\d+)\s*(?:years?|yrs?)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            return int(matches[0])
    
    return None

def extract_education(text: str) -> List[str]:
    """Extract education information from resume."""
    education = []
    
    # Look for degree patterns
    degree_patterns = [
        r'\b(?:bachelor|master|phd|doctorate)\s+(?:of|in)\s+([^\.]+)',
        r'\b(?:b\.s\.|m\.s\.|ph\.d\.|ba|ma)\s+(?:in\s+)?([^\.]+)',
        r'\b(?:university|college|institute)\s+of\s+([^\.]+)'
    ]
    
    for pattern in degree_patterns:
        matches = re.findall(pattern, text.lower())
        education.extend(matches)
    
    return list(set(education))

def calculate_ats_score(resume_keywords: List[str], job_keywords: List[str]) -> float:
    """Calculate ATS compatibility score."""
    if not job_keywords:
        return 0.0
    
    # Convert to sets for comparison
    resume_set = set(resume_keywords)
    job_set = set(job_keywords)
    
    # Calculate matches
    matches = resume_set.intersection(job_set)
    
    # Calculate score (percentage of job keywords found in resume)
    score = len(matches) / len(job_set) * 100
    
    return round(score, 2)

def generate_suggestions(resume_keywords: List[str], job_keywords: List[str], 
                        missing_keywords: List[str]) -> List[str]:
    """Generate optimization suggestions."""
    suggestions = []
    
    # Missing keywords suggestions
    if missing_keywords:
        suggestions.append(f"Add these keywords to your resume: {', '.join(missing_keywords[:5])}")
    
    # General ATS optimization tips
    suggestions.extend([
        "Use standard section headers: 'Experience', 'Education', 'Skills'",
        "Avoid graphics, tables, and complex formatting",
        "Use simple fonts like Arial, Calibri, or Times New Roman",
        "Include relevant keywords naturally in your descriptions",
        "Quantify achievements with numbers and percentages",
        "Use action verbs to start bullet points"
    ])
    
    # Specific suggestions based on analysis
    if len(resume_keywords) < 10:
        suggestions.append("Consider adding more specific skills and technologies")
    
    return suggestions

def analyze_job_description(job_text: str) -> Dict[str, Any]:
    """Analyze job description to extract relevant keywords."""
    cleaned_text = clean_text(job_text)
    keywords = extract_keywords(cleaned_text)
    
    # Categorize keywords
    categorized = {
        "technical": [kw for kw in keywords if kw in ATS_KEYWORDS["technical_skills"]],
        "soft_skills": [kw for kw in keywords if kw in ATS_KEYWORDS["soft_skills"]],
        "certifications": [kw for kw in keywords if kw in ATS_KEYWORDS["certifications"]]
    }
    
    return {
        "keywords": keywords,
        "categorized": categorized,
        "total_keywords": len(keywords)
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
            return HTMLResponse(content=html_content, media_type="text/html")
    except FileNotFoundError:
        return HTMLResponse(content="<h1>ATS Resume Analyzer API v2.0 is running</h1><p>index.html not found</p>")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error loading page</h1><p>{str(e)}</p>")

@app.post("/api/v1/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Upload a resume for ATS analysis."""
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF, DOCX, and DOC files are allowed"
        )
    
    # Validate file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 10MB"
        )
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = os.path.join("uploads", filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Extract text based on file type
        if file.filename.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        elif file.filename.lower().endswith(('.docx', '.doc')):
            extracted_text = extract_text_from_docx(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the uploaded file"
            )
        
        # Perform initial analysis
        keywords = extract_keywords(extracted_text)
        skills = extract_skills(extracted_text)
        experience_years = extract_experience_years(extracted_text)
        education = extract_education(extracted_text)
        
        # Store analysis results
        resume_analyses[file_id] = {
            "extracted_text": extracted_text,
            "keywords": keywords,
            "skills": skills,
            "experience_years": experience_years,
            "education": education,
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Resume uploaded and analyzed successfully",
                "file_id": file_id,
                "filename": file.filename,
                "file_size": len(content),
                "uploaded_at": datetime.utcnow().isoformat(),
                "analysis_summary": {
                    "keywords_found": len(keywords),
                    "skills_found": len(skills),
                    "experience_years": experience_years,
                    "education_items": len(education)
                }
            }
        )
        
    except Exception as e:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

@app.post("/api/v1/resume/analyze")
async def analyze_resume_ats(file_id: str = Form(...), job_description: str = Form(...)):
    """Analyze resume against a job description for ATS compatibility."""
    if file_id not in resume_analyses:
        raise HTTPException(status_code=404, detail="Resume analysis not found")
    
    # Get resume data
    resume_data = resume_analyses[file_id]
    
    # Analyze job description
    job_analysis = analyze_job_description(job_description)
    job_keywords = job_analysis["keywords"]
    
    # Calculate ATS score
    ats_score = calculate_ats_score(resume_data["keywords"], job_keywords)
    
    # Find matched and missing keywords
    resume_keywords_set = set(resume_data["keywords"])
    job_keywords_set = set(job_keywords)
    matched_keywords = list(resume_keywords_set.intersection(job_keywords_set))
    missing_keywords = list(job_keywords_set - resume_keywords_set)
    
    # Generate suggestions
    suggestions = generate_suggestions(resume_data["keywords"], job_keywords, missing_keywords)
    
    # Create analysis result
    analysis_result = {
        "file_id": file_id,
        "extracted_text": resume_data["extracted_text"][:500] + "..." if len(resume_data["extracted_text"]) > 500 else resume_data["extracted_text"],
        "keywords": resume_data["keywords"],
        "skills": resume_data["skills"],
        "experience_years": resume_data["experience_years"],
        "education": resume_data["education"],
        "ats_score": ats_score,
        "suggestions": suggestions,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "job_analysis": job_analysis,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }
    
    return JSONResponse(status_code=200, content=analysis_result)

@app.post("/api/v1/resume/optimize")
async def optimize_resume(request: ATSOptimizationRequest):
    """Provide detailed optimization suggestions for resume improvement."""
    # Analyze resume text
    resume_keywords = extract_keywords(request.resume_text)
    resume_skills = extract_skills(request.resume_text)
    
    # Analyze job description
    job_analysis = analyze_job_description(request.job_description)
    job_keywords = job_analysis["keywords"]
    
    # Calculate scores
    ats_score = calculate_ats_score(resume_keywords, job_keywords)
    
    # Find missing keywords
    resume_keywords_set = set(resume_keywords)
    job_keywords_set = set(job_keywords)
    missing_keywords = list(job_keywords_set - resume_keywords_set)
    
    # Generate detailed suggestions
    suggestions = []
    
    # Keyword suggestions
    if missing_keywords:
        suggestions.append({
            "category": "Missing Keywords",
            "suggestions": [
                f"Add '{keyword}' to your resume" for keyword in missing_keywords[:10]
            ]
        })
    
    # Formatting suggestions
    suggestions.append({
        "category": "Formatting",
        "suggestions": [
            "Use standard section headers (Experience, Education, Skills)",
            "Avoid tables, graphics, and complex formatting",
            "Use simple fonts (Arial, Calibri, Times New Roman)",
            "Keep formatting consistent throughout"
        ]
    })
    
    # Content suggestions
    suggestions.append({
        "category": "Content",
        "suggestions": [
            "Quantify achievements with numbers and percentages",
            "Use action verbs to start bullet points",
            "Include relevant keywords naturally in descriptions",
            "Focus on accomplishments rather than just responsibilities"
        ]
    })
    
    # Technical suggestions
    if len(resume_keywords) < 15:
        suggestions.append({
            "category": "Technical Skills",
            "suggestions": [
                "Add more specific technical skills and technologies",
                "Include programming languages, tools, and platforms",
                "Mention relevant certifications and training"
            ]
        })
    
    return JSONResponse(status_code=200, content={
        "ats_score": ats_score,
        "resume_keywords": resume_keywords,
        "job_keywords": job_keywords,
        "missing_keywords": missing_keywords,
        "suggestions": suggestions,
        "optimization_timestamp": datetime.utcnow().isoformat()
    })

@app.get("/api/v1/resume/{file_id}")
async def get_resume_analysis(file_id: str):
    """Get stored resume analysis results."""
    if file_id not in resume_analyses:
        raise HTTPException(status_code=404, detail="Resume analysis not found")
    
    return JSONResponse(status_code=200, content=resume_analyses[file_id])

@app.get("/api/v1/keywords")
async def get_common_keywords():
    """Get common ATS keywords by category."""
    return JSONResponse(status_code=200, content={
        "keywords": ATS_KEYWORDS,
        "total_categories": len(ATS_KEYWORDS)
    })

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "features": [
            "Resume upload and parsing",
            "ATS keyword analysis",
            "Job description matching",
            "Resume optimization suggestions",
            "Multi-format support (PDF, DOCX, DOC)"
        ]
    }

# Development server configuration
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 