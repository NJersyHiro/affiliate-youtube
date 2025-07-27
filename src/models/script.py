"""Script-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4


class ScriptStyle(Enum):
    """Script style enumeration."""
    HUMOROUS = "humorous"
    EDUCATIONAL = "educational"
    STORYTELLING = "storytelling"
    COMPARISON = "comparison"
    REVIEW = "review"
    DRAMATIC = "dramatic"
    CASUAL = "casual"
    PROFESSIONAL = "professional"


@dataclass
class ScriptSegment:
    """Represents a segment of the script."""
    id: str = field(default_factory=lambda: str(uuid4()))
    text: str = ""
    duration: float = 0.0  # Duration in seconds
    visual_description: str = ""  # Description of visuals for this segment
    transition_type: str = "cut"  # Transition to next segment
    emotion: str = "neutral"  # Emotion/tone for this segment
    emphasis_words: List[str] = field(default_factory=list)  # Words to emphasize
    
    @property
    def word_count(self) -> int:
        """Get word count of the segment."""
        return len(self.text.split())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "duration": self.duration,
            "visual_description": self.visual_description,
            "transition_type": self.transition_type,
            "emotion": self.emotion,
            "emphasis_words": self.emphasis_words,
            "word_count": self.word_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScriptSegment":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            text=data.get("text", ""),
            duration=data.get("duration", 0.0),
            visual_description=data.get("visual_description", ""),
            transition_type=data.get("transition_type", "cut"),
            emotion=data.get("emotion", "neutral"),
            emphasis_words=data.get("emphasis_words", [])
        )


@dataclass
class Script:
    """Represents a complete script for a YouTube Short."""
    id: str = field(default_factory=lambda: str(uuid4()))
    service_name: str = ""
    affiliate_url: str = ""
    style: ScriptStyle = ScriptStyle.HUMOROUS
    segments: List[ScriptSegment] = field(default_factory=list)
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_duration(self) -> float:
        """Get total duration of all segments."""
        return sum(segment.duration for segment in self.segments)
    
    @property
    def total_word_count(self) -> int:
        """Get total word count."""
        return sum(segment.word_count for segment in self.segments)
    
    @property
    def full_text(self) -> str:
        """Get full script text."""
        return " ".join(segment.text for segment in self.segments)
    
    def add_segment(self, segment: ScriptSegment) -> None:
        """Add a segment to the script."""
        self.segments.append(segment)
    
    def remove_segment(self, segment_id: str) -> bool:
        """Remove a segment by ID."""
        original_length = len(self.segments)
        self.segments = [s for s in self.segments if s.id != segment_id]
        return len(self.segments) < original_length
    
    def get_segment(self, segment_id: str) -> Optional[ScriptSegment]:
        """Get a segment by ID."""
        for segment in self.segments:
            if segment.id == segment_id:
                return segment
        return None
    
    def reorder_segments(self, segment_ids: List[str]) -> bool:
        """Reorder segments based on provided IDs."""
        if len(segment_ids) != len(self.segments):
            return False
            
        # Create a map of ID to segment
        segment_map = {s.id: s for s in self.segments}
        
        # Check all IDs are valid
        if not all(sid in segment_map for sid in segment_ids):
            return False
            
        # Reorder
        self.segments = [segment_map[sid] for sid in segment_ids]
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "service_name": self.service_name,
            "affiliate_url": self.affiliate_url,
            "style": self.style.value,
            "segments": [segment.to_dict() for segment in self.segments],
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "hashtags": self.hashtags,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "total_duration": self.total_duration,
            "total_word_count": self.total_word_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Script":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            service_name=data.get("service_name", ""),
            affiliate_url=data.get("affiliate_url", ""),
            style=ScriptStyle(data.get("style", "humorous")),
            segments=[ScriptSegment.from_dict(s) for s in data.get("segments", [])],
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            hashtags=data.get("hashtags", []),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            metadata=data.get("metadata", {})
        )