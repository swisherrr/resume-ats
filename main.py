from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid
from datetime import datetime
import PyPDF2
import io

# Initialize FastAPI application with metadata
app = FastAPI(
    title="ATS Resume Analyzer",
    description="A comprehensive backend system for ATS resume analysis",
    version="1.0.0"
)

# Create uploads directory if it doesn't exist
# This ensures the application can save uploaded files
os.makedirs("uploads", exist_ok=True)

@app.get("/")
async def root():
    """
    Root endpoint to verify the API is running.
    Useful for health checks and basic connectivity testing.
    """
    return {"message": "ATS Resume Analyzer API is running"}

@app.post("/api/v1/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload a PDF resume for analysis.
    
    This endpoint handles the core PDF upload functionality with comprehensive
    validation and error handling. It's designed to be secure and robust.
    
    Args:
        file: PDF file to upload (required)
        
    Returns:
        JSON response with upload status and file information
        
    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    # Step 1: Validate file type - only PDF files are allowed
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are allowed"
        )
    
    # Step 2: Validate file size - prevent DoS attacks and ensure reasonable storage usage
    # Maximum file size: 10MB (10 * 1024 * 1024 bytes)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 10MB"
        )
    
    # Step 3: Process the file upload with comprehensive error handling
    try:
        # Generate unique filename to prevent conflicts and ensure security
        # UUID4 provides cryptographically secure random identifiers
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = os.path.join("uploads", filename)
        
        # Step 4: Save the uploaded file to disk
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Step 5: Validate PDF content using PyPDF2
        # This ensures the file is actually a valid PDF, not just renamed
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            if len(pdf_reader.pages) == 0:
                # PDF is empty or corrupted
                raise HTTPException(
                    status_code=400,
                    detail="PDF file appears to be empty or corrupted"
                )
        except Exception as e:
            # Clean up the saved file if PDF validation fails
            # This prevents storage of invalid files
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file"
            )
        
        # Step 6: Return success response with file metadata
        # This provides the client with necessary information for further processing
        return JSONResponse(
            status_code=200,
            content={
                "message": "Resume uploaded successfully",
                "file_id": file_id,  # Unique identifier for the file
                "filename": file.filename,  # Original filename
                "file_size": len(content),  # File size in bytes
                "uploaded_at": datetime.utcnow().isoformat(),  # Upload timestamp
                "status": "ready_for_analysis"  # Current processing status
            }
        )
        
    except Exception as e:
        # Comprehensive error handling - clean up any saved files on error
        # This prevents orphaned files from failed uploads
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )

@app.get("/api/v1/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancer health checks.
    
    Returns basic status information and current timestamp.
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Development server configuration
if __name__ == "__main__":
    import uvicorn
    # Run the FastAPI application with uvicorn
    # host="0.0.0.0" allows external connections (not just localhost)
    # port=8000 is the standard development port
    uvicorn.run(app, host="0.0.0.0", port=8000) 