"""Video-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4


class VisualType(Enum):
    """Type of visual element."""
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
    SHAPE = "shape"
    ANIMATION = "animation"
    BACKGROUND = "background"
    OVERLAY = "overlay"
    TRANSITION = "transition"


@dataclass
class VideoSettings:
    """Video settings for generation."""
    resolution: Tuple[int, int] = (1080, 1920)  # Width x Height (9:16 for Shorts)
    fps: int = 30
    codec: str = "libx264"
    bitrate: str = "5M"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    format: str = "mp4"
    max_duration: int = 60  # Maximum duration in seconds
    
    @property
    def width(self) -> int:
        """Get video width."""
        return self.resolution[0]
    
    @property
    def height(self) -> int:
        """Get video height."""
        return self.resolution[1]
    
    @property
    def aspect_ratio(self) -> float:
        """Get aspect ratio."""
        return self.width / self.height
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resolution": list(self.resolution),
            "fps": self.fps,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "audio_codec": self.audio_codec,
            "audio_bitrate": self.audio_bitrate,
            "format": self.format,
            "max_duration": self.max_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoSettings":
        """Create from dictionary."""
        resolution = data.get("resolution", [1080, 1920])
        return cls(
            resolution=tuple(resolution),
            fps=data.get("fps", 30),
            codec=data.get("codec", "libx264"),
            bitrate=data.get("bitrate", "5M"),
            audio_codec=data.get("audio_codec", "aac"),
            audio_bitrate=data.get("audio_bitrate", "192k"),
            format=data.get("format", "mp4"),
            max_duration=data.get("max_duration", 60)
        )


@dataclass
class VisualElement:
    """Represents a visual element in the video."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: VisualType = VisualType.IMAGE
    file_path: Optional[Path] = None
    content: Optional[str] = None  # For text elements
    position: Tuple[int, int] = (0, 0)  # X, Y position
    size: Optional[Tuple[int, int]] = None  # Width, Height
    duration: float = 0.0  # Duration in seconds
    start_time: float = 0.0  # Start time in the video
    end_time: float = 0.0  # End time in the video
    animation: Optional[Dict[str, Any]] = None  # Animation properties
    style: Dict[str, Any] = field(default_factory=dict)  # Style properties
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """Check if the visual element is valid."""
        if self.type in [VisualType.IMAGE, VisualType.VIDEO]:
            return self.file_path is not None and self.file_path.exists()
        elif self.type == VisualType.TEXT:
            return bool(self.content)
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "file_path": str(self.file_path) if self.file_path else None,
            "content": self.content,
            "position": list(self.position),
            "size": list(self.size) if self.size else None,
            "duration": self.duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "animation": self.animation,
            "style": self.style,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualElement":
        """Create from dictionary."""
        file_path = data.get("file_path")
        position = data.get("position", [0, 0])
        size = data.get("size")
        
        return cls(
            id=data.get("id", str(uuid4())),
            type=VisualType(data.get("type", "image")),
            file_path=Path(file_path) if file_path else None,
            content=data.get("content"),
            position=tuple(position),
            size=tuple(size) if size else None,
            duration=data.get("duration", 0.0),
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", 0.0),
            animation=data.get("animation"),
            style=data.get("style", {}),
            metadata=data.get("metadata", {})
        )


@dataclass
class VideoClip:
    """Represents a video clip or segment."""
    id: str = field(default_factory=lambda: str(uuid4()))
    segment_id: str = ""  # ID of the script segment
    audio_clip_id: str = ""  # ID of the audio clip
    visual_elements: List[VisualElement] = field(default_factory=list)
    duration: float = 0.0  # Duration in seconds
    file_path: Optional[Path] = None  # Path to the generated clip
    settings: VideoSettings = field(default_factory=VideoSettings)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def exists(self) -> bool:
        """Check if the video file exists."""
        return self.file_path is not None and self.file_path.exists()
    
    @property
    def file_size(self) -> int:
        """Get file size in bytes."""
        if self.exists:
            return self.file_path.stat().st_size
        return 0
    
    def add_visual(self, visual: VisualElement) -> None:
        """Add a visual element."""
        self.visual_elements.append(visual)
    
    def remove_visual(self, visual_id: str) -> bool:
        """Remove a visual element by ID."""
        original_length = len(self.visual_elements)
        self.visual_elements = [v for v in self.visual_elements if v.id != visual_id]
        return len(self.visual_elements) < original_length
    
    def get_visual(self, visual_id: str) -> Optional[VisualElement]:
        """Get a visual element by ID."""
        for visual in self.visual_elements:
            if visual.id == visual_id:
                return visual
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "segment_id": self.segment_id,
            "audio_clip_id": self.audio_clip_id,
            "visual_elements": [v.to_dict() for v in self.visual_elements],
            "duration": self.duration,
            "file_path": str(self.file_path) if self.file_path else None,
            "settings": self.settings.to_dict(),
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "exists": self.exists,
            "file_size": self.file_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoClip":
        """Create from dictionary."""
        file_path = data.get("file_path")
        return cls(
            id=data.get("id", str(uuid4())),
            segment_id=data.get("segment_id", ""),
            audio_clip_id=data.get("audio_clip_id", ""),
            visual_elements=[VisualElement.from_dict(v) for v in data.get("visual_elements", [])],
            duration=data.get("duration", 0.0),
            file_path=Path(file_path) if file_path else None,
            settings=VideoSettings.from_dict(data.get("settings", {})),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            metadata=data.get("metadata", {})
        )