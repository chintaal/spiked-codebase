"""
Vector database management for file uploads and knowledge base
"""

import os
import json
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

import numpy as np
import faiss
import openai
from app.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, EMBEDDING_DIMENSION

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Vector DB paths
VECTOR_DB_DIR = Path("vector_db")
VECTOR_DB_DIR.mkdir(exist_ok=True)

INDEX_PATH = VECTOR_DB_DIR / "faiss_index.bin"
METADATA_PATH = VECTOR_DB_DIR / "embeddings_metadata.pkl"
FILE_REGISTRY_PATH = VECTOR_DB_DIR / "file_registry.json"

class VectorDBManager:
    """Manages vector database for uploaded files"""
    
    def __init__(self):
        self.index = None
        self.metadata = {}
        self.file_registry = {}
        self.load_existing_data()
    
    def load_existing_data(self):
        """Load existing vector database and metadata"""
        try:
            if INDEX_PATH.exists() and METADATA_PATH.exists():
                # Load FAISS index
                self.index = faiss.read_index(str(INDEX_PATH))
                
                # Load metadata
                with open(METADATA_PATH, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                logger.info(f"Loaded vector database with {self.index.ntotal} chunks")
            else:
                # Initialize new database
                self.index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
                self.metadata = {
                    "document_content": {},
                    "chunk_metadata": {},
                    "created_at": datetime.now().timestamp()
                }
                logger.info("Initialized new vector database")
            
            # Ensure metadata structure is correct for file management
            if "chunk_metadata" not in self.metadata:
                self.metadata["chunk_metadata"] = {}
            if "document_content" not in self.metadata:
                self.metadata["document_content"] = {}
            
            # Load file registry
            if FILE_REGISTRY_PATH.exists():
                with open(FILE_REGISTRY_PATH, 'r', encoding='utf-8') as f:
                    self.file_registry = json.load(f)
            else:
                self.file_registry = {}
                
        except Exception as e:
            logger.error(f"Error loading vector database: {str(e)}")
            # Initialize empty database on error
            self.index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
            self.metadata = {
                "document_content": {},
                "chunk_metadata": {},
                "created_at": datetime.now().timestamp()
            }
            self.file_registry = {}
    
    def save_database(self):
        """Save vector database to disk"""
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(INDEX_PATH))
            
            # Save metadata
            with open(METADATA_PATH, 'wb') as f:
                pickle.dump(self.metadata, f)
            
            # Save file registry
            with open(FILE_REGISTRY_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.file_registry, f, indent=2, ensure_ascii=False)
            
            logger.info("Vector database saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving vector database: {str(e)}")
            raise
    
    async def add_file_to_database(self, file_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Add a processed file to the vector database
        
        Args:
            file_id: Unique file identifier
            content: Extracted text content
            metadata: File metadata
            
        Returns:
            bool: Success status
        """
        try:
            # Check if file already exists
            if file_id in self.file_registry:
                logger.warning(f"File {file_id} already exists in database")
                return False
            
            # Split content into chunks
            chunks = self._split_into_chunks(content)
            
            if not chunks:
                logger.warning(f"No content chunks generated for file {file_id}")
                return False
            
            # Generate embeddings for chunks
            embeddings = await self._generate_embeddings(chunks)
            
            if not embeddings:
                logger.error(f"Failed to generate embeddings for file {file_id}")
                return False
            
            # Add to FAISS index
            embeddings_array = np.array(embeddings).astype('float32')
            start_index = self.index.ntotal
            self.index.add(embeddings_array)
            
            # Store chunk metadata
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_id}_chunk_{i}"
                chunk_index = start_index + i
                
                self.metadata["document_content"][chunk_id] = chunk
                self.metadata["chunk_metadata"][chunk_id] = {
                    "file_id": file_id,
                    "chunk_index": i,
                    "vector_index": chunk_index,
                    "chunk_length": len(chunk),
                    "created_at": datetime.now().timestamp()
                }
            
            # Register file
            self.file_registry[file_id] = {
                "metadata": metadata,
                "chunk_count": len(chunks),
                "start_vector_index": start_index,
                "end_vector_index": start_index + len(chunks) - 1,
                "added_at": datetime.now().isoformat()
            }
            
            # Save database
            self.save_database()
            
            logger.info(f"Successfully added file {file_id} with {len(chunks)} chunks to vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error adding file {file_id} to database: {str(e)}")
            return False
    
    async def remove_file_from_database(self, file_id: str) -> bool:
        """
        Remove a file from the vector database
        
        Args:
            file_id: File identifier to remove
            
        Returns:
            bool: Success status
        """
        try:
            if file_id not in self.file_registry:
                logger.warning(f"File {file_id} not found in database")
                return False
            
            # Get file info
            file_info = self.file_registry[file_id]
            
            # Remove chunk metadata
            chunks_to_remove = []
            for chunk_id in list(self.metadata["document_content"].keys()):
                if chunk_id.startswith(f"{file_id}_chunk_"):
                    chunks_to_remove.append(chunk_id)
            
            for chunk_id in chunks_to_remove:
                del self.metadata["document_content"][chunk_id]
                del self.metadata["chunk_metadata"][chunk_id]
            
            # Remove from file registry
            del self.file_registry[file_id]
            
            # Rebuild FAISS index (required for removal)
            await self._rebuild_index()
            
            logger.info(f"Successfully removed file {file_id} from vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error removing file {file_id} from database: {str(e)}")
            return False
    
    async def _rebuild_index(self):
        """Rebuild FAISS index after file removal"""
        try:
            # Create new index
            new_index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
            
            # Get all remaining chunks
            all_chunks = list(self.metadata["document_content"].values())
            
            if all_chunks:
                # Generate embeddings for all chunks
                embeddings = await self._generate_embeddings(all_chunks)
                
                if embeddings:
                    embeddings_array = np.array(embeddings).astype('float32')
                    new_index.add(embeddings_array)
                    
                    # Update vector indices in metadata
                    chunk_ids = list(self.metadata["document_content"].keys())
                    for i, chunk_id in enumerate(chunk_ids):
                        self.metadata["chunk_metadata"][chunk_id]["vector_index"] = i
            
            # Replace old index
            self.index = new_index
            
            # Save updated database
            self.save_database()
            
            logger.info("Vector index rebuilt successfully")
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {str(e)}")
            raise
    
    async def search_similar_chunks(self, query: str, k: int = 5, file_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar chunks in the database
        
        Args:
            query: Search query
            k: Number of results to return
            file_id: Optional file ID to limit search scope
            
        Returns:
            List of similar chunks with metadata
        """
        try:
            if self.index.ntotal == 0:
                return []
            
            # Generate query embedding
            query_embeddings = await self._generate_embeddings([query])
            if not query_embeddings:
                return []
            
            query_embedding = np.array([query_embeddings[0]]).astype('float32')
            
            # Search the index
            distances, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
            
            # Get results
            results = []
            chunk_ids = list(self.metadata["document_content"].keys())
            
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if 0 <= idx < len(chunk_ids):
                    chunk_id = chunk_ids[idx]
                    
                    # Handle both old and new chunk formats
                    if chunk_id in self.metadata["chunk_metadata"]:
                        # New file management format
                        chunk_metadata = self.metadata["chunk_metadata"][chunk_id]
                        
                        # Filter by file_id if specified
                        if file_id and chunk_metadata["file_id"] != file_id:
                            continue
                        
                        result = {
                            "chunk_id": chunk_id,
                            "content": self.metadata["document_content"][chunk_id],
                            "distance": float(distance),
                            "similarity_score": float(1.0 / (1.0 + float(distance))),
                            "file_id": chunk_metadata["file_id"],
                            "chunk_index": chunk_metadata["chunk_index"],
                            "file_metadata": self.file_registry.get(chunk_metadata["file_id"], {}).get("metadata", {}),
                            "source_info": {
                                "filename": self.file_registry.get(chunk_metadata["file_id"], {}).get("metadata", {}).get("original_filename", "Unknown"),
                                "file_type": self.file_registry.get(chunk_metadata["file_id"], {}).get("metadata", {}).get("file_type", "Unknown"),
                                "description": self.file_registry.get(chunk_metadata["file_id"], {}).get("metadata", {}).get("user_description", ""),
                                "upload_date": self.file_registry.get(chunk_metadata["file_id"], {}).get("added_at", ""),
                                "chunk_number": chunk_metadata["chunk_index"] + 1,
                                "source_type": "uploaded_document"
                            }
                        }
                    else:
                        # Old knowledge base format
                        if file_id:
                            # Skip old format chunks when filtering by file_id
                            continue
                        
                        # Extract file info from old chunk_id format
                        file_name = chunk_id.rsplit('_', 1)[0] if '_' in chunk_id else chunk_id
                        chunk_index = chunk_id.rsplit('_', 1)[1] if '_' in chunk_id else "0"
                        
                        result = {
                            "chunk_id": chunk_id,
                            "content": self.metadata["document_content"][chunk_id],
                            "distance": float(distance),
                            "similarity_score": float(1.0 / (1.0 + float(distance))),
                            "file_id": file_name,  # Use filename as file_id for old chunks
                            "chunk_index": chunk_index,
                            "file_metadata": {
                                "original_filename": file_name,
                                "file_type": "Knowledge Base Document",
                                "source": "legacy_knowledge_base"
                            },
                            "source_info": {
                                "filename": file_name,
                                "file_type": "Knowledge Base Document", 
                                "description": f"Legacy knowledge base: {file_name.replace('_processed.txt', '').replace('_', ' ')}",
                                "upload_date": "Legacy Import",
                                "chunk_number": int(chunk_index) + 1 if chunk_index.isdigit() else 1,
                                "source_type": "knowledge_base"
                            }
                        }
                    
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching chunks: {str(e)}")
            return []
    
    def get_file_list(self) -> List[Dict[str, Any]]:
        """Get list of all files in the database"""
        try:
            files = []
            for file_id, file_info in self.file_registry.items():
                file_data = {
                    "file_id": file_id,
                    "chunk_count": file_info["chunk_count"],
                    "added_at": file_info["added_at"],
                    **file_info["metadata"]
                }
                files.append(file_data)
            
            return sorted(files, key=lambda x: x["added_at"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting file list: {str(e)}")
            return []
    
    def get_file_details(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific file"""
        try:
            if file_id not in self.file_registry:
                return None
            
            file_info = self.file_registry[file_id]
            
            # Get chunk information
            chunk_details = []
            for chunk_id in self.metadata["document_content"].keys():
                if chunk_id.startswith(f"{file_id}_chunk_"):
                    chunk_metadata = self.metadata["chunk_metadata"][chunk_id]
                    chunk_details.append({
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_metadata["chunk_index"],
                        "content_preview": self.metadata["document_content"][chunk_id][:200] + "...",
                        "chunk_length": chunk_metadata["chunk_length"]
                    })
            
            return {
                "file_id": file_id,
                "metadata": file_info["metadata"],
                "chunk_count": file_info["chunk_count"],
                "added_at": file_info["added_at"],
                "chunks": sorted(chunk_details, key=lambda x: x["chunk_index"])
            }
            
        except Exception as e:
            logger.error(f"Error getting file details for {file_id}: {str(e)}")
            return None
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            total_files = len(self.file_registry)
            total_chunks = self.index.ntotal if self.index else 0
            
            # Calculate total content size
            total_content_size = sum(
                len(content) for content in self.metadata["document_content"].values()
            )
            
            # File type distribution
            file_types = {}
            for file_info in self.file_registry.values():
                file_type = file_info["metadata"].get("file_type", "Unknown")
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            return {
                "total_files": total_files,
                "total_chunks": total_chunks,
                "total_content_size": total_content_size,
                "file_types": file_types,
                "database_created_at": self.metadata.get("created_at"),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {}
    
    def _split_into_chunks(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split content into overlapping chunks"""
        if not content.strip():
            return []
        
        chunks = []
        start = 0
        content_length = len(content)
        
        while start < content_length:
            # Find end position
            end = start + chunk_size
            
            # If this isn't the last chunk, try to break at a sentence or word boundary
            if end < content_length:
                # Look for sentence boundary
                sentence_end = content.rfind('.', start, end)
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    word_end = content.rfind(' ', start, end)
                    if word_end > start + chunk_size // 2:
                        end = word_end
            
            # Extract chunk
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position (with overlap)
            start = max(start + chunk_size - overlap, end)
            
            # Prevent infinite loop
            if start <= end - chunk_size + overlap:
                start = end
        
        return chunks
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            if not texts:
                return []
            
            response = client.embeddings.create(
                model=OPENAI_EMBEDDING_MODEL,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return []

# Global instance
vector_db_manager = VectorDBManager()
