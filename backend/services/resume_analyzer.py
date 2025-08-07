import PyPDF2
import pdfplumber
import io
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
from docx import Document
from typing import List, Dict, Optional, Any
import hashlib
import json
from datetime import datetime

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

class ResumeAnalyzer:
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
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
            # Try pdfplumber first for better text extraction
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            print(f"pdfplumber failed, trying PyPDF2: {e}")
            try:
                # Fallback to PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
            except Exception as e2:
                print(f"PyPDF2 also failed: {e2}")
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
            print(f"Error extracting text from DOCX: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-]', ' ', text)
        return text.lower()

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using NLP."""
        # Tokenize and clean
        tokens = word_tokenize(self.clean_text(text))
        
        # Remove stopwords
        stop_words = set(stopwords.words('english'))
        tokens = [token for token in tokens if token.lower() not in stop_words and len(token) > 2]
        
        # Lemmatize
        lemmatized_tokens = [self.lemmatizer.lemmatize(token) for token in tokens]
        
        # Get unique keywords
        keywords = list(set(lemmatized_tokens))
        
        return keywords

    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text."""
        skills = []
        text_lower = text.lower()
        
        # Check for technical skills
        for skill in self.ats_keywords["technical_skills"]:
            if skill in text_lower:
                skills.append(skill)
        
        # Check for soft skills
        for skill in self.ats_keywords["soft_skills"]:
            if skill in text_lower:
                skills.append(skill)
        
        return list(set(skills))

    def extract_experience_years(self, text: str) -> Optional[int]:
        """Extract years of experience from text."""
        # Look for patterns like "X years of experience"
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
        
        # Look for degree patterns
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
        
        # Count matched keywords
        matched_keywords = set(resume_keywords) & set(job_keywords)
        
        # Calculate score based on match percentage
        match_percentage = len(matched_keywords) / len(job_keywords) * 100
        
        # Normalize to 0-100 scale
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
        
        # Generate cache key
        content_hash = hashlib.md5(file_content).hexdigest()
        cache_key = f"resume:analysis:{content_hash}"
        
        # Check Redis cache first
        cached_result = await self.redis.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
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
        
        # Cache result in Redis
        await self.redis.setex(cache_key, 3600, json.dumps(result))  # Cache for 1 hour
        
        return result

resume_analyzer = None  # Will be initialized with database connection 