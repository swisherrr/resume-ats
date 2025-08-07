from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class ResumeModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    filename: str
    s3_key: Optional[str] = None
    parsed_content: Dict[str, Any] = {}
    analysis_results: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class JobPostingModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    title: str
    company: str
    location: Dict[str, Any] = {}  # GeoJSON format
    requirements: List[str] = []
    salary_range: Dict[str, Any] = {}
    technologies: List[str] = []
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = ""

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class SkillsTaxonomyModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    skill_name: str
    category: str
    aliases: List[str] = []
    learning_resources: List[str] = []
    demand_score: float = 0.0
    salary_impact: float = 0.0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Request/Response Models
class ResumeAnalysisRequest(BaseModel):
    job_description: str
    target_keywords: List[str] = []

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