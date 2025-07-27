"""Script processing module for segmentation and timing adjustments."""

from typing import List, Dict, Any, Optional, Tuple
import re
import json
from datetime import timedelta

from ..models.script import Script, ScriptSegment, ScriptStyle
from ..utils import Config, get_logger, handle_errors, dev_error_logger
from ..utils.exceptions import ScriptGenerationError


class ScriptProcessor:
    """Process scripts for optimal TTS and video generation."""
    
    # Japanese character reading speeds (characters per second)
    READING_SPEEDS = {
        "slow": 4.0,      # Slow, clear speech
        "normal": 5.5,    # Normal conversational speed
        "fast": 7.0,      # Fast, energetic speech
        "ultra_fast": 8.5 # Very fast (for disclaimers, etc.)
    }
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the script processor.
        
        Args:
            config: Configuration object. If not provided, will create default.
        """
        self.config = config or Config()
        self.logger = get_logger(__name__)
        
        # Get default reading speed from config
        self.default_speed = self.config.get("script.reading_speed", "normal")
        
    @handle_errors("ScriptProcessor")
    def process_script(self, script: Script) -> Script:
        """Process a script for optimal delivery.
        
        Args:
            script: The script to process
            
        Returns:
            Processed script with optimized timing and segments
        """
        self.logger.info(f"Processing script for {script.service_name}")
        
        # Validate and adjust timing
        script = self._validate_timing(script)
        
        # Split long segments if needed
        script = self._split_long_segments(script)
        
        # Add pauses and breathing points
        script = self._add_natural_pauses(script)
        
        # Optimize emphasis and emotion
        script = self._optimize_delivery(script)
        
        # Final timing adjustment
        script = self._adjust_final_timing(script)
        
        self.logger.info(f"Script processed: {len(script.segments)} segments, "
                        f"{script.total_duration:.1f}s total duration")
        
        return script
    
    def _validate_timing(self, script: Script) -> Script:
        """Validate and adjust segment timing based on text length."""
        for segment in script.segments:
            # Calculate expected duration based on text length
            char_count = len(segment.text)
            speed = self.READING_SPEEDS[self.default_speed]
            expected_duration = char_count / speed
            
            # Add buffer for pauses between words
            pause_buffer = 0.2 + (char_count * 0.01)  # Base pause + proportional
            expected_duration += pause_buffer
            
            # Adjust if the original duration is way off
            if abs(segment.duration - expected_duration) > 2.0:
                self.logger.warning(
                    f"Adjusting segment duration from {segment.duration:.1f}s "
                    f"to {expected_duration:.1f}s"
                )
                segment.duration = expected_duration
        
        return script
    
    def _split_long_segments(self, script: Script) -> Script:
        """Split segments that are too long for comfortable delivery."""
        max_segment_duration = self.config.get("script.max_segment_duration", 15.0)
        new_segments = []
        
        for segment in script.segments:
            if segment.duration <= max_segment_duration:
                new_segments.append(segment)
                continue
            
            # Split the segment
            split_segments = self._split_segment(segment, max_segment_duration)
            new_segments.extend(split_segments)
            self.logger.info(f"Split long segment into {len(split_segments)} parts")
        
        # Replace segments
        script.segments = new_segments
        return script
    
    def _split_segment(self, segment: ScriptSegment, max_duration: float) -> List[ScriptSegment]:
        """Split a single segment into multiple parts."""
        # Split by sentences first
        sentences = self._split_into_sentences(segment.text)
        
        if len(sentences) <= 1:
            # Can't split by sentences, split by phrases
            return self._split_by_phrases(segment, max_duration)
        
        # Group sentences into segments
        segments = []
        current_text = ""
        current_duration = 0.0
        speed = self.READING_SPEEDS[self.default_speed]
        
        for sentence in sentences:
            sentence_duration = len(sentence) / speed + 0.3  # Add pause
            
            if current_duration + sentence_duration > max_duration and current_text:
                # Create segment
                segments.append(ScriptSegment(
                    text=current_text.strip(),
                    duration=current_duration,
                    visual_description=segment.visual_description,
                    emotion=segment.emotion,
                    emphasis_words=[w for w in segment.emphasis_words if w in current_text]
                ))
                current_text = sentence
                current_duration = sentence_duration
            else:
                current_text += " " + sentence if current_text else sentence
                current_duration += sentence_duration
        
        # Add remaining text
        if current_text:
            segments.append(ScriptSegment(
                text=current_text.strip(),
                duration=current_duration,
                visual_description=segment.visual_description,
                emotion=segment.emotion,
                emphasis_words=[w for w in segment.emphasis_words if w in current_text]
            ))
        
        return segments
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences (Japanese-aware)."""
        # Japanese sentence endings
        sentence_endings = r'[。！？!?]+'
        
        # Split by sentence endings
        sentences = re.split(f'({sentence_endings})', text)
        
        # Reconstruct sentences with their endings
        result = []
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            elif sentences[i].strip():
                result.append(sentences[i])
        
        return [s.strip() for s in result if s.strip()]
    
    def _split_by_phrases(self, segment: ScriptSegment, max_duration: float) -> List[ScriptSegment]:
        """Split by phrases when sentence splitting isn't possible."""
        # Split by common Japanese particles and conjunctions
        phrase_markers = r'[、,]|(?:が|で|に|を|は|と|の|から|まで|より)'
        
        parts = re.split(f'({phrase_markers})', segment.text)
        
        # Group parts
        segments = []
        current_text = ""
        current_duration = 0.0
        speed = self.READING_SPEEDS[self.default_speed]
        
        for i, part in enumerate(parts):
            part_duration = len(part) / speed
            
            if current_duration + part_duration > max_duration and current_text:
                segments.append(ScriptSegment(
                    text=current_text.strip(),
                    duration=current_duration,
                    visual_description=segment.visual_description,
                    emotion=segment.emotion
                ))
                current_text = part
                current_duration = part_duration
            else:
                current_text += part
                current_duration += part_duration
        
        # Add remaining
        if current_text:
            segments.append(ScriptSegment(
                text=current_text.strip(),
                duration=current_duration,
                visual_description=segment.visual_description,
                emotion=segment.emotion
            ))
        
        return segments if segments else [segment]
    
    def _add_natural_pauses(self, script: Script) -> Script:
        """Add natural pauses for breathing and emphasis."""
        for segment in script.segments:
            # Add pauses after punctuation
            segment.text = self._insert_pauses(segment.text)
            
            # Adjust duration for pauses
            pause_count = segment.text.count('<pause>')
            segment.duration += pause_count * 0.3  # 0.3s per pause
        
        return script
    
    def _insert_pauses(self, text: str) -> str:
        """Insert pause markers in text."""
        # Add pauses after major punctuation
        text = re.sub(r'([。！？!?])\s*', r'\1<pause>', text)
        
        # Add smaller pauses after commas
        text = re.sub(r'([、,])\s*', r'\1<pause:0.2>', text)
        
        # Add pauses before conjunctions
        conjunctions = ['しかし', 'でも', 'ただし', 'それでは', 'さて']
        for conj in conjunctions:
            text = text.replace(conj, f'<pause:0.3>{conj}')
        
        return text
    
    def _optimize_delivery(self, script: Script) -> Script:
        """Optimize emotion and emphasis for better delivery."""
        for segment in script.segments:
            # Auto-detect emphasis words if not provided
            if not segment.emphasis_words:
                segment.emphasis_words = self._detect_emphasis_words(segment.text)
            
            # Adjust emotion based on content
            if segment.emotion == "neutral":
                segment.emotion = self._detect_emotion(segment.text)
        
        return script
    
    def _detect_emphasis_words(self, text: str) -> List[str]:
        """Detect words that should be emphasized."""
        emphasis_patterns = [
            r'すごい|素晴らしい|最高|最新|革新的|画期的',  # Positive descriptors
            r'なんと|実は|ついに|初めて',  # Surprise/revelation
            r'今だけ|限定|特別|お得',  # Urgency/exclusivity
            r'\d+[％%]|[一二三四五六七八九十百千万億]+倍',  # Numbers/percentages
        ]
        
        emphasis_words = []
        for pattern in emphasis_patterns:
            matches = re.findall(pattern, text)
            emphasis_words.extend(matches)
        
        return list(set(emphasis_words))  # Remove duplicates
    
    def _detect_emotion(self, text: str) -> str:
        """Detect appropriate emotion for text."""
        # Excitement indicators
        if re.search(r'[！!]{2,}|すごい|最高|素晴らしい', text):
            return "excited"
        
        # Question/curiosity indicators
        if re.search(r'[？?]|どう|なぜ|どうして', text):
            return "curious"
        
        # Happy indicators
        if re.search(r'嬉しい|楽しい|幸せ|笑|😊|😄', text):
            return "happy"
        
        # Surprise indicators
        if re.search(r'なんと|実は|驚き|びっくり', text):
            return "surprised"
        
        return "neutral"
    
    def _adjust_final_timing(self, script: Script) -> Script:
        """Make final timing adjustments to fit within duration limits."""
        max_duration = self.config.get("video.max_duration", 60)
        total_duration = script.total_duration
        
        if total_duration <= max_duration:
            return script
        
        # Need to speed up delivery
        speed_factor = max_duration / total_duration
        self.logger.warning(f"Speeding up script by {(1-speed_factor)*100:.1f}% "
                          f"to fit within {max_duration}s limit")
        
        for segment in script.segments:
            segment.duration *= speed_factor
        
        return script
    
    @handle_errors("ScriptProcessor")
    def export_for_tts(self, script: Script) -> List[Dict[str, Any]]:
        """Export script segments in format optimized for TTS.
        
        Args:
            script: The processed script
            
        Returns:
            List of segment dictionaries ready for TTS
        """
        tts_segments = []
        
        for segment in script.segments:
            # Clean text for TTS
            tts_text = self._prepare_text_for_tts(segment.text)
            
            tts_segment = {
                "id": segment.id,
                "text": tts_text,
                "duration": segment.duration,
                "emotion": segment.emotion,
                "emphasis_words": segment.emphasis_words,
                "speaking_rate": self._calculate_speaking_rate(segment),
                "pitch_contour": self._generate_pitch_contour(segment),
                "volume_adjustments": self._generate_volume_adjustments(segment)
            }
            
            tts_segments.append(tts_segment)
        
        return tts_segments
    
    def _prepare_text_for_tts(self, text: str) -> str:
        """Prepare text for TTS processing."""
        # Convert pause markers to SSML or provider-specific format
        text = text.replace('<pause>', '... ')
        text = re.sub(r'<pause:([\d.]+)>', '... ', text)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _calculate_speaking_rate(self, segment: ScriptSegment) -> float:
        """Calculate speaking rate for segment."""
        base_rate = 1.0
        
        # Adjust based on emotion
        emotion_rates = {
            "excited": 1.1,
            "happy": 1.05,
            "curious": 0.95,
            "surprised": 1.15,
            "neutral": 1.0
        }
        
        return base_rate * emotion_rates.get(segment.emotion, 1.0)
    
    def _generate_pitch_contour(self, segment: ScriptSegment) -> List[Tuple[float, float]]:
        """Generate pitch contour for natural intonation."""
        # Simple pitch contour based on emotion
        emotion_pitches = {
            "excited": [(0, 1.1), (0.5, 1.2), (1.0, 1.15)],
            "happy": [(0, 1.05), (0.5, 1.1), (1.0, 1.05)],
            "curious": [(0, 1.0), (0.8, 1.1), (1.0, 1.2)],  # Rising
            "surprised": [(0, 1.0), (0.3, 1.3), (1.0, 1.1)],
            "neutral": [(0, 1.0), (0.5, 1.0), (1.0, 0.95)]
        }
        
        return emotion_pitches.get(segment.emotion, [(0, 1.0), (1.0, 1.0)])
    
    def _generate_volume_adjustments(self, segment: ScriptSegment) -> Dict[str, float]:
        """Generate volume adjustments for emphasis."""
        adjustments = {}
        
        # Increase volume for emphasis words
        for word in segment.emphasis_words:
            adjustments[word] = 1.2  # 20% louder
        
        return adjustments
    
    @handle_errors("ScriptProcessor")
    def create_script_summary(self, script: Script) -> Dict[str, Any]:
        """Create a summary of the processed script.
        
        Args:
            script: The processed script
            
        Returns:
            Summary dictionary with key metrics
        """
        summary = {
            "service_name": script.service_name,
            "style": script.style.value,
            "total_duration": round(script.total_duration, 1),
            "segment_count": len(script.segments),
            "total_words": script.total_word_count,
            "average_segment_duration": round(script.total_duration / len(script.segments), 1) if script.segments else 0,
            "emotions_used": list(set(s.emotion for s in script.segments)),
            "has_emphasis": any(s.emphasis_words for s in script.segments),
            "title": script.title,
            "tags": script.tags,
            "hashtags": script.hashtags
        }
        
        return summary