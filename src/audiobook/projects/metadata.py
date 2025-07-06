"""
Project metadata management for the audiobook system.
"""
import json
import time
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path

from ..config import PathManager, ProjectPreset

@dataclass
class ChunkMetadata:
    """Metadata for a single audio chunk."""
    chunk_number: int
    text: str
    start_index: int
    end_index: int
    audio_file: str
    duration: float
    is_complete_sentence: bool
    voice_name: Optional[str] = None
    generation_params: Optional[Dict] = None
    last_modified: float = time.time()

@dataclass
class VoiceInfo:
    """Information about a voice used in the project."""
    name: str
    display_name: str
    description: Optional[str] = None
    exaggeration: float = 0.5
    temperature: float = 0.8
    cfg_weight: float = 0.5
    enable_normalization: bool = True
    target_level_db: float = -18.0

@dataclass
class ProjectMetadata:
    """Complete project metadata."""
    name: str
    text_content: str
    creation_date: float
    last_modified: float
    project_type: str  # 'single_voice' or 'multi_voice'
    voice_info: Dict[str, VoiceInfo]
    chunks: List[ChunkMetadata]
    settings: Dict
    status: str = 'in_progress'  # 'in_progress', 'completed', 'failed'
    total_duration: float = 0.0
    version: str = '1.0.0'

class MetadataManager:
    """Manages project metadata operations."""
    
    def __init__(self, project_name: str, preset: ProjectPreset = ProjectPreset()):
        self.project_name = project_name
        self.preset = preset
        self.path_manager = PathManager()
        
    def _get_metadata_path(self) -> Path:
        """Get the path to the project's metadata file."""
        return self.path_manager.get_project_metadata_path(self.project_name)
    
    def load(self) -> ProjectMetadata:
        """Load project metadata from file."""
        try:
            metadata_path = self._get_metadata_path()
            if not metadata_path.exists():
                raise FileNotFoundError(f"No metadata found for project: {self.project_name}")
                
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Convert voice info dictionaries to VoiceInfo objects
            voice_info = {
                name: VoiceInfo(**info) if isinstance(info, dict) else info
                for name, info in data['voice_info'].items()
            }
            
            # Convert chunk dictionaries to ChunkMetadata objects
            chunks = [ChunkMetadata(**chunk) for chunk in data['chunks']]
            
            # Create ProjectMetadata object
            return ProjectMetadata(
                **{**data, 'voice_info': voice_info, 'chunks': chunks}
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to load metadata: {str(e)}")
    
    def save(self, metadata: ProjectMetadata) -> None:
        """Save project metadata to file."""
        try:
            metadata_path = self._get_metadata_path()
            
            # Convert metadata to dictionary
            data = asdict(metadata)
            
            # Ensure the project directory exists
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with pretty formatting
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise RuntimeError(f"Failed to save metadata: {str(e)}")
    
    def create(
        self,
        text_content: str,
        project_type: str,
        voice_info: Dict[str, Union[VoiceInfo, Dict]],
        settings: Optional[Dict] = None
    ) -> ProjectMetadata:
        """Create new project metadata."""
        # Convert voice_info dictionaries to VoiceInfo objects if needed
        processed_voice_info = {
            name: VoiceInfo(**info) if isinstance(info, dict) else info
            for name, info in voice_info.items()
        }
        
        # Create metadata object
        now = time.time()
        metadata = ProjectMetadata(
            name=self.project_name,
            text_content=text_content,
            creation_date=now,
            last_modified=now,
            project_type=project_type,
            voice_info=processed_voice_info,
            chunks=[],
            settings=settings or {},
            status='in_progress'
        )
        
        # Save to file
        self.save(metadata)
        return metadata
    
    def update_chunk(
        self,
        chunk_number: int,
        updates: Dict
    ) -> None:
        """Update metadata for a specific chunk."""
        metadata = self.load()
        
        # Find and update the chunk
        for chunk in metadata.chunks:
            if chunk.chunk_number == chunk_number:
                for key, value in updates.items():
                    setattr(chunk, key, value)
                break
        else:
            raise ValueError(f"Chunk {chunk_number} not found")
        
        # Update last modified time
        metadata.last_modified = time.time()
        
        # Save changes
        self.save(metadata)
    
    def add_chunk(self, chunk: ChunkMetadata) -> None:
        """Add a new chunk to the project metadata."""
        metadata = self.load()
        
        # Check for duplicate chunk numbers
        if any(c.chunk_number == chunk.chunk_number for c in metadata.chunks):
            raise ValueError(f"Chunk {chunk.chunk_number} already exists")
        
        # Add the new chunk
        metadata.chunks.append(chunk)
        metadata.chunks.sort(key=lambda x: x.chunk_number)
        
        # Update last modified time
        metadata.last_modified = time.time()
        
        # Save changes
        self.save(metadata)
    
    def update_status(
        self,
        status: str,
        total_duration: Optional[float] = None
    ) -> None:
        """Update project status and optionally total duration."""
        metadata = self.load()
        metadata.status = status
        
        if total_duration is not None:
            metadata.total_duration = total_duration
            
        metadata.last_modified = time.time()
        self.save(metadata)
    
    def get_chunk(self, chunk_number: int) -> Optional[ChunkMetadata]:
        """Get metadata for a specific chunk."""
        metadata = self.load()
        for chunk in metadata.chunks:
            if chunk.chunk_number == chunk_number:
                return chunk
        return None
    
    def get_voice_info(self, voice_name: str) -> Optional[VoiceInfo]:
        """Get information about a specific voice."""
        metadata = self.load()
        return metadata.voice_info.get(voice_name)
    
    def update_voice_info(
        self,
        voice_name: str,
        updates: Dict
    ) -> None:
        """Update information for a specific voice."""
        metadata = self.load()
        
        if voice_name not in metadata.voice_info:
            raise ValueError(f"Voice {voice_name} not found")
            
        voice_info = metadata.voice_info[voice_name]
        for key, value in updates.items():
            setattr(voice_info, key, value)
            
        metadata.last_modified = time.time()
        self.save(metadata) 