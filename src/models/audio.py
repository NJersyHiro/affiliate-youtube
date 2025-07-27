"""Audio-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4


@dataclass
class AudioSettings:
    """Audio settings for TTS generation."""
    provider: str = "google_cloud"  # google_cloud, azure, aws
    language_code: str = "ja-JP"
    voice_name: str = "ja-JP-Neural2-B"
    speaking_rate: float = 1.0  # 0.25 to 4.0
    pitch: float = 0.0  # -20.0 to 20.0
    volume_gain_db: float = 0.0  # -96.0 to 16.0
    audio_encoding: str = "MP3"  # MP3, LINEAR16, OGG_OPUS
    sample_rate_hz: int = 24000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "provider": self.provider,
            "language_code": self.language_code,
            "voice_name": self.voice_name,
            "speaking_rate": self.speaking_rate,
            "pitch": self.pitch,
            "volume_gain_db": self.volume_gain_db,
            "audio_encoding": self.audio_encoding,
            "sample_rate_hz": self.sample_rate_hz
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioSettings":
        """Create from dictionary."""
        return cls(
            provider=data.get("provider", "google_cloud"),
            language_code=data.get("language_code", "ja-JP"),
            voice_name=data.get("voice_name", "ja-JP-Neural2-B"),
            speaking_rate=data.get("speaking_rate", 1.0),
            pitch=data.get("pitch", 0.0),
            volume_gain_db=data.get("volume_gain_db", 0.0),
            audio_encoding=data.get("audio_encoding", "MP3"),
            sample_rate_hz=data.get("sample_rate_hz", 24000)
        )


@dataclass
class AudioClip:
    """Represents an audio clip generated from text."""
    id: str = field(default_factory=lambda: str(uuid4()))
    segment_id: str = ""  # ID of the script segment
    text: str = ""
    file_path: Optional[Path] = None
    duration: float = 0.0  # Duration in seconds
    settings: AudioSettings = field(default_factory=AudioSettings)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def exists(self) -> bool:
        """Check if the audio file exists."""
        return self.file_path is not None and self.file_path.exists()
    
    @property
    def file_size(self) -> int:
        """Get file size in bytes."""
        if self.exists:
            return self.file_path.stat().st_size
        return 0
    
    @property
    def file_extension(self) -> str:
        """Get file extension."""
        if self.file_path:
            return self.file_path.suffix
        return ""
    
    def delete_file(self) -> bool:
        """Delete the audio file."""
        if self.exists:
            try:
                self.file_path.unlink()
                return True
            except Exception:
                return False
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "segment_id": self.segment_id,
            "text": self.text,
            "file_path": str(self.file_path) if self.file_path else None,
            "duration": self.duration,
            "settings": self.settings.to_dict(),
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "exists": self.exists,
            "file_size": self.file_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioClip":
        """Create from dictionary."""
        file_path = data.get("file_path")
        return cls(
            id=data.get("id", str(uuid4())),
            segment_id=data.get("segment_id", ""),
            text=data.get("text", ""),
            file_path=Path(file_path) if file_path else None,
            duration=data.get("duration", 0.0),
            settings=AudioSettings.from_dict(data.get("settings", {})),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            metadata=data.get("metadata", {})
        )