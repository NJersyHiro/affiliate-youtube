"""Project-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from .script import Script
from .audio import AudioClip
from .video import VideoClip


class ProjectStatus(Enum):
    """Project status enumeration."""
    DRAFT = "draft"
    SCRIPT_GENERATED = "script_generated"
    AUDIO_GENERATED = "audio_generated"
    VISUALS_GENERATED = "visuals_generated"
    VIDEO_COMPOSED = "video_composed"
    READY_TO_UPLOAD = "ready_to_upload"
    UPLOADED = "uploaded"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class VideoMetadata:
    """Metadata for YouTube video upload."""
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    category_id: str = "22"  # People & Blogs
    privacy_status: str = "private"  # private, unlisted, public
    made_for_kids: bool = False
    default_language: str = "ja"
    recording_date: Optional[datetime] = None
    thumbnail_path: Optional[Path] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "category_id": self.category_id,
            "privacy_status": self.privacy_status,
            "made_for_kids": self.made_for_kids,
            "default_language": self.default_language,
            "recording_date": self.recording_date.isoformat() if self.recording_date else None,
            "thumbnail_path": str(self.thumbnail_path) if self.thumbnail_path else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoMetadata":
        """Create from dictionary."""
        recording_date = data.get("recording_date")
        thumbnail_path = data.get("thumbnail_path")
        
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category_id=data.get("category_id", "22"),
            privacy_status=data.get("privacy_status", "private"),
            made_for_kids=data.get("made_for_kids", False),
            default_language=data.get("default_language", "ja"),
            recording_date=datetime.fromisoformat(recording_date) if recording_date else None,
            thumbnail_path=Path(thumbnail_path) if thumbnail_path else None
        )


@dataclass
class Project:
    """Represents a complete YouTube Shorts generation project."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    service_name: str = ""
    affiliate_url: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    script: Optional[Script] = None
    audio_clips: List[AudioClip] = field(default_factory=list)
    video_clips: List[VideoClip] = field(default_factory=list)
    final_video_path: Optional[Path] = None
    video_metadata: VideoMetadata = field(default_factory=VideoMetadata)
    youtube_video_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_complete(self) -> bool:
        """Check if the project is complete."""
        return self.status == ProjectStatus.UPLOADED
    
    @property
    def has_script(self) -> bool:
        """Check if script is generated."""
        return self.script is not None
    
    @property
    def has_audio(self) -> bool:
        """Check if audio is generated."""
        return len(self.audio_clips) > 0
    
    @property
    def has_video(self) -> bool:
        """Check if video is composed."""
        return self.final_video_path is not None and self.final_video_path.exists()
    
    @property
    def project_dir(self) -> Path:
        """Get project directory path."""
        return Path("output") / "projects" / self.id
    
    def update_status(self, status: ProjectStatus) -> None:
        """Update project status and timestamp."""
        self.status = status
        self.updated_at = datetime.now()
    
    def add_audio_clip(self, clip: AudioClip) -> None:
        """Add an audio clip."""
        self.audio_clips.append(clip)
        self.updated_at = datetime.now()
    
    def add_video_clip(self, clip: VideoClip) -> None:
        """Add a video clip."""
        self.video_clips.append(clip)
        self.updated_at = datetime.now()
    
    def get_audio_clip(self, clip_id: str) -> Optional[AudioClip]:
        """Get audio clip by ID."""
        for clip in self.audio_clips:
            if clip.id == clip_id:
                return clip
        return None
    
    def get_video_clip(self, clip_id: str) -> Optional[VideoClip]:
        """Get video clip by ID."""
        for clip in self.video_clips:
            if clip.id == clip_id:
                return clip
        return None
    
    def cleanup_files(self) -> None:
        """Clean up all generated files."""
        # Clean audio files
        for audio in self.audio_clips:
            audio.delete_file()
            
        # Clean video clips
        for video in self.video_clips:
            if video.exists:
                video.file_path.unlink()
                
        # Clean final video
        if self.final_video_path and self.final_video_path.exists():
            self.final_video_path.unlink()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "service_name": self.service_name,
            "affiliate_url": self.affiliate_url,
            "status": self.status.value,
            "script": self.script.to_dict() if self.script else None,
            "audio_clips": [clip.to_dict() for clip in self.audio_clips],
            "video_clips": [clip.to_dict() for clip in self.video_clips],
            "final_video_path": str(self.final_video_path) if self.final_video_path else None,
            "video_metadata": self.video_metadata.to_dict(),
            "youtube_video_id": self.youtube_video_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Create from dictionary."""
        script_data = data.get("script")
        final_video_path = data.get("final_video_path")
        
        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            service_name=data.get("service_name", ""),
            affiliate_url=data.get("affiliate_url", ""),
            status=ProjectStatus(data.get("status", "draft")),
            script=Script.from_dict(script_data) if script_data else None,
            audio_clips=[AudioClip.from_dict(a) for a in data.get("audio_clips", [])],
            video_clips=[VideoClip.from_dict(v) for v in data.get("video_clips", [])],
            final_video_path=Path(final_video_path) if final_video_path else None,
            video_metadata=VideoMetadata.from_dict(data.get("video_metadata", {})),
            youtube_video_id=data.get("youtube_video_id"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            metadata=data.get("metadata", {})
        )
    
    def save_to_file(self, file_path: Optional[Path] = None) -> Path:
        """Save project to JSON file."""
        import json
        
        if file_path is None:
            file_path = self.project_dir / "project.json"
            
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            
        return file_path
    
    @classmethod
    def load_from_file(cls, file_path: Path) -> "Project":
        """Load project from JSON file."""
        import json
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return cls.from_dict(data)