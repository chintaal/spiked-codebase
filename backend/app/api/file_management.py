"""
File upload and management API endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import shutil
from pathlib import Path
import uuid
import json
from datetime import datetime

from app.utils.file_processor import file_processor, is_supported_file, get_file_type, UPLOAD_DIR, PROCESSED_DIR
from app.utils.vector_db_manager import vector_db_manager
from pydantic import BaseModel

# Create router
router = APIRouter(prefix="/api/files", tags=["File Management"])

# Response models
class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[str] = None
    metadata: Optional[dict] = None

class FileListResponse(BaseModel):
    files: List[dict]
    total_count: int
    database_stats: dict

class FileDetailsResponse(BaseModel):
    file_details: Optional[dict]
    success: bool
    message: str

class SearchResponse(BaseModel):
    results: List[dict]
    query: str
    total_results: int
    sources: List[dict] = []  # Add sources summary

# File upload endpoint
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None)
):
    """
    Upload and process a document file
    
    Supports: PDF, DOCX, DOC, TXT, MD, PPTX, PPT, and image files
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not is_supported_file(file.filename):
            supported_types = ", ".join([".pdf", ".docx", ".txt", ".md", ".pptx", ".jpg", ".png"])
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported types: {supported_types}"
            )
        
        # Check file size (limit to 50MB)
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Process the file
        processing_result = await file_processor.process_file(file_path, file.filename)
        
        if not processing_result["success"]:
            # Clean up uploaded file on processing failure
            if file_path.exists():
                file_path.unlink()
            
            raise HTTPException(
                status_code=500, 
                detail=f"File processing failed: {processing_result.get('error', 'Unknown error')}"
            )
        
        file_id = processing_result["file_id"]
        extracted_text = processing_result["extracted_text"]
        metadata = processing_result["metadata"]
        
        # Add description if provided
        if description:
            metadata["user_description"] = description
        
        # Add to vector database
        vector_db_success = await vector_db_manager.add_file_to_database(
            file_id=file_id,
            content=extracted_text,
            metadata=metadata
        )
        
        if not vector_db_success:
            # Clean up files if vector DB addition fails
            if file_path.exists():
                file_path.unlink()
            processed_file = PROCESSED_DIR / f"{file_id}_processed.txt"
            if processed_file.exists():
                processed_file.unlink()
            metadata_file = PROCESSED_DIR / f"{file_id}_metadata.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            raise HTTPException(
                status_code=500,
                detail="Failed to add file to vector database"
            )
        
        return FileUploadResponse(
            success=True,
            message="File uploaded and processed successfully",
            file_id=file_id,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Get list of uploaded files
@router.get("/list", response_model=FileListResponse)
async def list_files():
    """Get list of all uploaded files with metadata"""
    try:
        files = vector_db_manager.get_file_list()
        stats = vector_db_manager.get_database_stats()
        
        return FileListResponse(
            files=files,
            total_count=len(files),
            database_stats=stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file list: {str(e)}")

# Get file details
@router.get("/details/{file_id}", response_model=FileDetailsResponse)
async def get_file_details(file_id: str):
    """Get detailed information about a specific file"""
    try:
        file_details = vector_db_manager.get_file_details(file_id)
        
        if not file_details:
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileDetailsResponse(
            file_details=file_details,
            success=True,
            message="File details retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file details: {str(e)}")

# Delete file
@router.delete("/delete/{file_id}")
async def delete_file(file_id: str):
    """Delete a file and remove it from the vector database"""
    try:
        # Get file details first
        file_details = vector_db_manager.get_file_details(file_id)
        if not file_details:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Remove from vector database
        removal_success = await vector_db_manager.remove_file_from_database(file_id)
        
        if not removal_success:
            raise HTTPException(status_code=500, detail="Failed to remove file from vector database")
        
        # Clean up physical files
        processed_file = PROCESSED_DIR / f"{file_id}_processed.txt"
        metadata_file = PROCESSED_DIR / f"{file_id}_metadata.json"
        
        if processed_file.exists():
            processed_file.unlink()
        
        if metadata_file.exists():
            metadata_file.unlink()
        
        # Try to find and remove original file (if still exists)
        for file_path in UPLOAD_DIR.glob(f"*"):
            try:
                # Check if this file corresponds to our file_id
                # (This is a best-effort cleanup since we don't store original file mapping)
                pass
            except:
                pass
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"File {file_id} deleted successfully"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

# Search files
@router.post("/search", response_model=SearchResponse)
async def search_files(
    query: str,
    limit: int = 10,
    file_id: Optional[str] = None
):
    """Search for content across uploaded files"""
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        results = await vector_db_manager.search_similar_chunks(
            query=query,
            k=limit,
            file_id=file_id
        )
        
        # Create sources summary for NotebookLM-style attribution
        sources_map = {}
        for result in results:
            source_info = result.get("source_info", {})
            filename = source_info.get("filename", "Unknown")
            
            if filename not in sources_map:
                sources_map[filename] = {
                    "filename": filename,
                    "file_type": source_info.get("file_type", "Unknown"),
                    "description": source_info.get("description", ""),
                    "source_type": source_info.get("source_type", "unknown"),
                    "chunk_count": 0,
                    "relevance_scores": []
                }
            
            sources_map[filename]["chunk_count"] += 1
            sources_map[filename]["relevance_scores"].append(result.get("similarity_score", 0))
        
        # Calculate average relevance per source
        sources = []
        for source_data in sources_map.values():
            avg_relevance = sum(source_data["relevance_scores"]) / len(source_data["relevance_scores"])
            sources.append({
                "filename": source_data["filename"],
                "file_type": source_data["file_type"], 
                "description": source_data["description"],
                "source_type": source_data["source_type"],
                "chunks_found": source_data["chunk_count"],
                "average_relevance": round(avg_relevance, 3)
            })
        
        # Sort sources by relevance
        sources.sort(key=lambda x: x["average_relevance"], reverse=True)
        
        return SearchResponse(
            results=results,
            query=query,
            total_results=len(results),
            sources=sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# Get database statistics
@router.get("/stats")
async def get_database_stats():
    """Get vector database statistics"""
    try:
        stats = vector_db_manager.get_database_stats()
        return JSONResponse(content=stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")

# Rebuild vector database
@router.post("/rebuild-db")
async def rebuild_vector_database():
    """Rebuild the vector database (use with caution)"""
    try:
        # Get all files
        files = vector_db_manager.get_file_list()
        
        if not files:
            return JSONResponse(
                content={
                    "success": True,
                    "message": "No files to rebuild database with"
                }
            )
        
        # Clear current database
        vector_db_manager.index = vector_db_manager.index.__class__(vector_db_manager.index.d)
        vector_db_manager.metadata = {
            "document_content": {},
            "chunk_metadata": {},
            "created_at": datetime.now().timestamp()
        }
        vector_db_manager.file_registry = {}
        
        # Re-add all files
        rebuilt_count = 0
        failed_files = []
        
        for file_info in files:
            file_id = file_info["file_id"]
            
            try:
                # Read processed file content
                processed_file = PROCESSED_DIR / f"{file_id}_processed.txt"
                if not processed_file.exists():
                    failed_files.append(file_id)
                    continue
                
                with open(processed_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Re-add to database
                success = await vector_db_manager.add_file_to_database(
                    file_id=file_id,
                    content=content,
                    metadata=file_info
                )
                
                if success:
                    rebuilt_count += 1
                else:
                    failed_files.append(file_id)
                    
            except Exception as e:
                failed_files.append(file_id)
                continue
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Database rebuilt successfully. {rebuilt_count} files processed.",
                "rebuilt_count": rebuilt_count,
                "failed_files": failed_files
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild database: {str(e)}")

# Download processed file
@router.get("/download/{file_id}")
async def download_processed_file(file_id: str):
    """Download the processed text file"""
    try:
        processed_file = PROCESSED_DIR / f"{file_id}_processed.txt"
        
        if not processed_file.exists():
            raise HTTPException(status_code=404, detail="Processed file not found")
        
        # Get original filename for response
        file_details = vector_db_manager.get_file_details(file_id)
        original_filename = "processed_document.txt"
        
        if file_details and file_details.get("metadata"):
            original_name = file_details["metadata"].get("original_filename", "")
            if original_name:
                name_without_ext = Path(original_name).stem
                original_filename = f"{name_without_ext}_processed.txt"
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=processed_file,
            filename=original_filename,
            media_type="text/plain"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")
