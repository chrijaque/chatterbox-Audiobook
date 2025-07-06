"""
Project file storage management for the audiobook system.
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional, Union
import logging

from ..config import PathManager, ProjectPreset

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages project file storage operations."""
    
    def __init__(self, project_name: str, preset: ProjectPreset = ProjectPreset()):
        self.project_name = project_name
        self.preset = preset
        self.path_manager = PathManager()
        
    def get_project_dir(self) -> Path:
        """Get the project directory path."""
        return self.path_manager.get_project_dir(self.project_name)
    
    def get_audio_dir(self) -> Path:
        """Get the project's audio directory path."""
        return self.path_manager.get_project_audio_dir(self.project_name)
    
    def get_temp_dir(self) -> Path:
        """Get the project's temporary directory path."""
        return self.path_manager.get_temp_project_dir(self.project_name)
    
    def ensure_directories(self) -> None:
        """Ensure all necessary project directories exist."""
        self.get_project_dir().mkdir(parents=True, exist_ok=True)
        self.get_audio_dir().mkdir(parents=True, exist_ok=True)
        self.get_temp_dir().mkdir(parents=True, exist_ok=True)
    
    def get_chunk_path(self, chunk_number: int, temp: bool = False) -> Path:
        """Get the path for a chunk's audio file."""
        filename = f"chunk_{chunk_number:04d}.{self.preset.output_format}"
        if temp:
            return self.get_temp_dir() / filename
        return self.get_audio_dir() / filename
    
    def get_final_output_path(self, output_format: Optional[str] = None) -> Path:
        """Get the path for the final combined audio file."""
        format_ext = output_format or self.preset.output_format
        return self.get_project_dir() / f"{self.project_name}.{format_ext}"
    
    def save_chunk(
        self,
        chunk_number: int,
        audio_data: bytes,
        temp: bool = False
    ) -> Path:
        """Save audio data as a chunk file."""
        try:
            chunk_path = self.get_chunk_path(chunk_number, temp)
            chunk_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(chunk_path, 'wb') as f:
                f.write(audio_data)
                
            return chunk_path
            
        except Exception as e:
            logger.error(f"Failed to save chunk {chunk_number}: {str(e)}")
            raise
    
    def load_chunk(
        self,
        chunk_number: int,
        temp: bool = False
    ) -> bytes:
        """Load audio data from a chunk file."""
        try:
            chunk_path = self.get_chunk_path(chunk_number, temp)
            
            if not chunk_path.exists():
                raise FileNotFoundError(f"Chunk {chunk_number} not found")
                
            with open(chunk_path, 'rb') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Failed to load chunk {chunk_number}: {str(e)}")
            raise
    
    def delete_chunk(
        self,
        chunk_number: int,
        temp: bool = False
    ) -> None:
        """Delete a chunk file."""
        try:
            chunk_path = self.get_chunk_path(chunk_number, temp)
            
            if chunk_path.exists():
                chunk_path.unlink()
                
        except Exception as e:
            logger.error(f"Failed to delete chunk {chunk_number}: {str(e)}")
            raise
    
    def save_final_output(
        self,
        audio_data: bytes,
        output_format: Optional[str] = None
    ) -> Path:
        """Save the final combined audio file."""
        try:
            output_path = self.get_final_output_path(output_format)
            
            with open(output_path, 'wb') as f:
                f.write(audio_data)
                
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save final output: {str(e)}")
            raise
    
    def cleanup_temp_files(self) -> None:
        """Clean up temporary project files."""
        try:
            temp_dir = self.get_temp_dir()
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            logger.error(f"Failed to cleanup temporary files: {str(e)}")
            raise
    
    def list_chunks(self, temp: bool = False) -> List[Path]:
        """List all chunk files in order."""
        try:
            directory = self.get_temp_dir() if temp else self.get_audio_dir()
            
            if not directory.exists():
                return []
                
            # Get all chunk files and sort by number
            chunk_files = [f for f in directory.glob(f"chunk_*.{self.preset.output_format}")]
            chunk_files.sort(key=lambda x: int(x.stem.split('_')[1]))
            
            return chunk_files
            
        except Exception as e:
            logger.error(f"Failed to list chunks: {str(e)}")
            raise
    
    def move_chunk_to_final(self, chunk_number: int) -> None:
        """Move a chunk from temporary to final storage."""
        try:
            temp_path = self.get_chunk_path(chunk_number, temp=True)
            final_path = self.get_chunk_path(chunk_number, temp=False)
            
            if not temp_path.exists():
                raise FileNotFoundError(f"Temporary chunk {chunk_number} not found")
                
            # Ensure target directory exists
            final_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            shutil.move(str(temp_path), str(final_path))
            
        except Exception as e:
            logger.error(f"Failed to move chunk {chunk_number} to final storage: {str(e)}")
            raise
    
    def backup_project(self, backup_dir: Union[str, Path]) -> Path:
        """Create a backup of the entire project."""
        try:
            backup_dir = Path(backup_dir)
            project_backup_dir = backup_dir / self.project_name
            
            # Ensure backup directory exists
            project_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy project files
            shutil.copytree(
                self.get_project_dir(),
                project_backup_dir,
                dirs_exist_ok=True
            )
            
            return project_backup_dir
            
        except Exception as e:
            logger.error(f"Failed to create project backup: {str(e)}")
            raise
    
    def restore_from_backup(self, backup_dir: Union[str, Path]) -> None:
        """Restore project from a backup."""
        try:
            backup_dir = Path(backup_dir)
            project_backup_dir = backup_dir / self.project_name
            
            if not project_backup_dir.exists():
                raise FileNotFoundError(f"Backup not found: {project_backup_dir}")
                
            # Remove existing project files
            project_dir = self.get_project_dir()
            if project_dir.exists():
                shutil.rmtree(project_dir)
                
            # Copy backup files
            shutil.copytree(project_backup_dir, project_dir)
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {str(e)}")
            raise
    
    def get_project_size(self) -> int:
        """Get total size of project files in bytes."""
        try:
            total_size = 0
            project_dir = self.get_project_dir()
            
            for dirpath, _, filenames in os.walk(project_dir):
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    total_size += file_path.stat().st_size
                    
            return total_size
            
        except Exception as e:
            logger.error(f"Failed to calculate project size: {str(e)}")
            raise 