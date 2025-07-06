"""Path management for the audiobook application."""

import os
from pathlib import Path
from typing import Optional

class PathManager:
    """Manages paths for various components of the audiobook application."""
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize path manager with optional base directory."""
        if base_dir is None:
            base_dir = os.getenv('AUDIOBOOK_BASE_DIR', os.getcwd())
        self.base_dir = Path(base_dir)
        
        # Define standard directories
        self.voice_library_dir = self.base_dir / "voice_library"
        self.output_dir = self.voice_library_dir / "output"
        self.samples_dir = self.voice_library_dir / "samples"
        self.clones_dir = self.voice_library_dir / "clones"
        self.test_dir = self.voice_library_dir / "test"
        self.projects_dir = self.base_dir / "audiobook_projects"
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create all required directories if they don't exist."""
        directories = [
            self.voice_library_dir,
            self.output_dir,
            self.samples_dir,
            self.clones_dir,
            self.test_dir,
            self.projects_dir,
            self.get_tts_output_path()
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_voice_path(self, voice_id: str) -> Path:
        """Get the path for a specific voice."""
        return self.clones_dir / voice_id
    
    def get_output_path(self, filename: str) -> Path:
        """Get the path for an output file."""
        return self.output_dir / filename
    
    def get_sample_path(self, filename: str) -> Path:
        """Get the path for a sample file."""
        return self.samples_dir / filename
    
    def get_test_path(self, filename: str) -> Path:
        """Get the path for a test file."""
        return self.test_dir / filename
    
    def get_project_path(self, project_id: str) -> Path:
        """Get the path for a specific project."""
        return self.projects_dir / project_id
    
    def get_voice_samples_path(self) -> Path:
        """Get the path for voice samples."""
        return self.samples_dir
    
    def get_voice_clones_path(self) -> Path:
        """Get the path for voice clones."""
        return self.clones_dir
    
    def get_tts_output_path(self) -> Path:
        """Get the path for TTS output files."""
        return self.output_dir / "tts"
    
    def get_relative_path(self, path: Path) -> str:
        """Get a path relative to the base directory."""
        try:
            return str(path.relative_to(self.base_dir))
        except ValueError:
            return str(path)
    
    def is_valid_voice_path(self, path: Path) -> bool:
        """Check if a path is a valid voice directory."""
        try:
            path.relative_to(self.clones_dir)
            return path.is_dir()
        except ValueError:
            return False
    
    def is_valid_project_path(self, path: Path) -> bool:
        """Check if a path is a valid project directory."""
        try:
            path.relative_to(self.projects_dir)
            return path.is_dir()
        except ValueError:
            return False
    
    def cleanup_temp_files(self, older_than_days: int = 7):
        """Clean up temporary files older than specified days."""
        # TODO: Implement cleanup logic
        pass
