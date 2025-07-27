"""Visual generation module for creating video elements."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
import tempfile
import random

from PIL import Image, ImageDraw, ImageFont
import numpy as np

from ..models.video import VisualElement, VisualType, VideoSettings
from ..models.script import ScriptSegment
from ..utils import Config, get_logger, handle_errors, dev_error_logger
from ..utils.exceptions import VideoProcessingError


class VisualGenerator:
    """Generate visual elements for YouTube Shorts videos."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the visual generator.
        
        Args:
            config: Configuration object. If not provided, will create default.
        """
        self.config = config or Config()
        self.logger = get_logger(__name__)
        
        # Get video settings
        self.video_settings = self._get_video_settings()
        
        # Ensure output directories exist
        self.output_dir = self.config.get_output_path(
            self.config.get("output.visuals_dir", "visuals")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load assets
        self.assets_dir = Path("assets")
        self._load_assets()
        
    def _get_video_settings(self) -> VideoSettings:
        """Get video settings from config."""
        video_config = self.config.get("video", {})
        resolution = video_config.get("resolution", {"width": 1080, "height": 1920})
        
        return VideoSettings(
            resolution=(resolution["width"], resolution["height"]),
            fps=video_config.get("fps", 30),
            codec=video_config.get("codec", "libx264"),
            bitrate=video_config.get("bitrate", "5M"),
            audio_codec=video_config.get("audio_codec", "aac"),
            audio_bitrate=video_config.get("audio_bitrate", "192k"),
            format=video_config.get("format", "mp4"),
            max_duration=video_config.get("max_duration", 60)
        )
    
    def _load_assets(self) -> None:
        """Load visual assets."""
        self.backgrounds = []
        self.icons = {}
        self.fonts = {}
        
        # Load backgrounds if available
        bg_dir = self.assets_dir / "backgrounds"
        if bg_dir.exists():
            for bg_file in bg_dir.glob("*.png"):
                self.backgrounds.append(bg_file)
            self.logger.info(f"Loaded {len(self.backgrounds)} background images")
        
        # Load default font paths
        self.fonts["default"] = self._get_default_font()
        self.fonts["title"] = self._get_title_font()
        self.fonts["subtitle"] = self._get_subtitle_font()
        
    def _get_default_font(self) -> str:
        """Get default font path."""
        # Try to find a Japanese font
        font_candidates = [
            "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "C:\\Windows\\Fonts\\msgothic.ttc"
        ]
        
        for font_path in font_candidates:
            if os.path.exists(font_path):
                return font_path
                
        # Fallback to PIL default
        return None
    
    def _get_title_font(self) -> str:
        """Get title font path."""
        # For now, use the same as default
        return self._get_default_font()
    
    def _get_subtitle_font(self) -> str:
        """Get subtitle font path."""
        # For now, use the same as default
        return self._get_default_font()
    
    @handle_errors("VisualGenerator")
    def generate_segment_visuals(
        self,
        segment: ScriptSegment,
        duration: float,
        project_id: str
    ) -> List[VisualElement]:
        """Generate visual elements for a script segment.
        
        Args:
            segment: The script segment
            duration: Duration of the segment in seconds
            project_id: Project ID for organizing output
            
        Returns:
            List of VisualElement objects
        """
        visual_elements = []
        
        # Create project visuals directory
        project_visuals_dir = self.output_dir / project_id
        project_visuals_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate background
        bg_element = self._generate_background(
            segment,
            duration,
            project_visuals_dir
        )
        if bg_element:
            visual_elements.append(bg_element)
        
        # Generate text overlays
        text_elements = self._generate_text_overlays(
            segment,
            duration,
            project_visuals_dir
        )
        visual_elements.extend(text_elements)
        
        # Generate decorative elements based on emotion
        decorative_elements = self._generate_decorative_elements(
            segment,
            duration,
            project_visuals_dir
        )
        visual_elements.extend(decorative_elements)
        
        self.logger.info(f"Generated {len(visual_elements)} visual elements "
                        f"for segment {segment.id}")
        
        return visual_elements
    
    def _generate_background(
        self,
        segment: ScriptSegment,
        duration: float,
        output_dir: Path
    ) -> Optional[VisualElement]:
        """Generate background for segment."""
        try:
            # Choose background style based on emotion
            bg_style = self._get_background_style(segment.emotion)
            
            # Create background image
            bg_image = self._create_background_image(bg_style)
            
            # Save background
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bg_path = output_dir / f"bg_{segment.id}_{timestamp}.png"
            bg_image.save(bg_path)
            
            # Create visual element
            bg_element = VisualElement(
                type=VisualType.BACKGROUND,
                file_path=bg_path,
                position=(0, 0),
                size=self.video_settings.resolution,
                duration=duration,
                start_time=0.0,
                end_time=duration,
                style={
                    "opacity": 1.0,
                    "blend_mode": "normal"
                }
            )
            
            return bg_element
            
        except Exception as e:
            self.logger.error(f"Failed to generate background: {e}")
            return None
    
    def _get_background_style(self, emotion: str) -> Dict[str, Any]:
        """Get background style based on emotion."""
        styles = {
            "excited": {
                "type": "gradient",
                "colors": ["#FF6B6B", "#FFE66D"],
                "direction": "diagonal",
                "animation": "pulse"
            },
            "happy": {
                "type": "gradient",
                "colors": ["#4ECDC4", "#44A08D"],
                "direction": "vertical",
                "animation": "subtle"
            },
            "surprised": {
                "type": "gradient",
                "colors": ["#FC466B", "#3F5EFB"],
                "direction": "radial",
                "animation": "zoom"
            },
            "curious": {
                "type": "gradient",
                "colors": ["#667EEA", "#764BA2"],
                "direction": "horizontal",
                "animation": "drift"
            },
            "neutral": {
                "type": "gradient",
                "colors": ["#E0E0E0", "#FFFFFF"],
                "direction": "vertical",
                "animation": "none"
            }
        }
        
        return styles.get(emotion, styles["neutral"])
    
    def _create_background_image(self, style: Dict[str, Any]) -> Image.Image:
        """Create background image based on style."""
        width, height = self.video_settings.resolution
        
        # Create base image
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        if style["type"] == "gradient":
            # Parse colors
            color1 = self._hex_to_rgb(style["colors"][0])
            color2 = self._hex_to_rgb(style["colors"][1])
            
            # Create gradient based on direction
            if style["direction"] == "vertical":
                self._draw_vertical_gradient(draw, width, height, color1, color2)
            elif style["direction"] == "horizontal":
                self._draw_horizontal_gradient(draw, width, height, color1, color2)
            elif style["direction"] == "diagonal":
                self._draw_diagonal_gradient(draw, width, height, color1, color2)
            elif style["direction"] == "radial":
                self._draw_radial_gradient(draw, width, height, color1, color2)
            else:
                # Default to vertical
                self._draw_vertical_gradient(draw, width, height, color1, color2)
        
        return image
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _draw_vertical_gradient(
        self,
        draw: ImageDraw.Draw,
        width: int,
        height: int,
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int]
    ) -> None:
        """Draw vertical gradient."""
        for y in range(height):
            # Calculate interpolation factor
            factor = y / height
            
            # Interpolate colors
            r = int(color1[0] * (1 - factor) + color2[0] * factor)
            g = int(color1[1] * (1 - factor) + color2[1] * factor)
            b = int(color1[2] * (1 - factor) + color2[2] * factor)
            
            # Draw line
            draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    def _draw_horizontal_gradient(
        self,
        draw: ImageDraw.Draw,
        width: int,
        height: int,
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int]
    ) -> None:
        """Draw horizontal gradient."""
        for x in range(width):
            factor = x / width
            r = int(color1[0] * (1 - factor) + color2[0] * factor)
            g = int(color1[1] * (1 - factor) + color2[1] * factor)
            b = int(color1[2] * (1 - factor) + color2[2] * factor)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))
    
    def _draw_diagonal_gradient(
        self,
        draw: ImageDraw.Draw,
        width: int,
        height: int,
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int]
    ) -> None:
        """Draw diagonal gradient."""
        # Simple implementation - blend based on distance from top-left
        max_distance = (width**2 + height**2)**0.5
        
        # Create numpy array for faster processing
        img_array = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in range(height):
            for x in range(width):
                # Distance from top-left corner
                distance = (x**2 + y**2)**0.5
                factor = distance / max_distance
                
                # Interpolate colors
                r = int(color1[0] * (1 - factor) + color2[0] * factor)
                g = int(color1[1] * (1 - factor) + color2[1] * factor)
                b = int(color1[2] * (1 - factor) + color2[2] * factor)
                
                img_array[y, x] = [r, g, b]
        
        # Convert back to PIL Image
        gradient_img = Image.fromarray(img_array)
        draw.bitmap((0, 0), gradient_img, fill=None)
    
    def _draw_radial_gradient(
        self,
        draw: ImageDraw.Draw,
        width: int,
        height: int,
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int]
    ) -> None:
        """Draw radial gradient."""
        center_x, center_y = width // 2, height // 2
        max_radius = min(width, height) // 2
        
        # Draw concentric circles
        for radius in range(max_radius, 0, -2):
            factor = (max_radius - radius) / max_radius
            r = int(color1[0] * (1 - factor) + color2[0] * factor)
            g = int(color1[1] * (1 - factor) + color2[1] * factor)
            b = int(color1[2] * (1 - factor) + color2[2] * factor)
            
            draw.ellipse(
                [center_x - radius, center_y - radius,
                 center_x + radius, center_y + radius],
                fill=(r, g, b)
            )
    
    def _generate_text_overlays(
        self,
        segment: ScriptSegment,
        duration: float,
        output_dir: Path
    ) -> List[VisualElement]:
        """Generate text overlay elements."""
        text_elements = []
        
        # Split text into chunks for display
        text_chunks = self._split_text_for_display(segment.text)
        
        # Calculate timing for each chunk
        chunk_duration = duration / len(text_chunks)
        
        for i, chunk in enumerate(text_chunks):
            # Create text image
            text_image = self._create_text_image(
                chunk,
                segment.emotion,
                segment.emphasis_words
            )
            
            if text_image:
                # Save text image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                text_path = output_dir / f"text_{segment.id}_{i}_{timestamp}.png"
                text_image.save(text_path)
                
                # Calculate position (centered, lower third)
                text_width, text_height = text_image.size
                x_pos = (self.video_settings.width - text_width) // 2
                y_pos = int(self.video_settings.height * 0.7)
                
                # Create visual element
                text_element = VisualElement(
                    type=VisualType.TEXT,
                    file_path=text_path,
                    content=chunk,
                    position=(x_pos, y_pos),
                    size=(text_width, text_height),
                    duration=chunk_duration,
                    start_time=i * chunk_duration,
                    end_time=(i + 1) * chunk_duration,
                    animation={
                        "type": "fade_in_out",
                        "in_duration": 0.3,
                        "out_duration": 0.3
                    },
                    style={
                        "font_size": 48,
                        "color": "#FFFFFF",
                        "outline_color": "#000000",
                        "outline_width": 3
                    }
                )
                
                text_elements.append(text_element)
        
        return text_elements
    
    def _split_text_for_display(self, text: str, max_chars: int = 30) -> List[str]:
        """Split text into chunks suitable for display."""
        # Split by punctuation first
        import re
        sentences = re.split(r'([。！？!?、,])', text)
        
        # Reconstruct with punctuation
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def _create_text_image(
        self,
        text: str,
        emotion: str,
        emphasis_words: List[str]
    ) -> Optional[Image.Image]:
        """Create text overlay image."""
        try:
            # Get font
            font_path = self.fonts.get("default")
            font_size = 48
            
            if font_path:
                font = ImageFont.truetype(font_path, font_size)
            else:
                # Use default font
                font = ImageFont.load_default()
            
            # Calculate text size
            # Create a temporary image to measure text
            temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # Get text bounding box
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0] + 20  # Add padding
            text_height = bbox[3] - bbox[1] + 20
            
            # Create actual image
            image = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Draw text with outline
            x, y = 10, 10
            
            # Draw outline
            outline_width = 3
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 255))
            
            # Draw main text
            text_color = self._get_text_color(emotion)
            draw.text((x, y), text, font=font, fill=text_color)
            
            return image
            
        except Exception as e:
            self.logger.error(f"Failed to create text image: {e}")
            return None
    
    def _get_text_color(self, emotion: str) -> Tuple[int, int, int, int]:
        """Get text color based on emotion."""
        colors = {
            "excited": (255, 255, 0, 255),  # Yellow
            "happy": (255, 255, 255, 255),  # White
            "surprised": (255, 100, 100, 255),  # Light red
            "curious": (100, 200, 255, 255),  # Light blue
            "neutral": (255, 255, 255, 255)  # White
        }
        
        return colors.get(emotion, colors["neutral"])
    
    def _generate_decorative_elements(
        self,
        segment: ScriptSegment,
        duration: float,
        output_dir: Path
    ) -> List[VisualElement]:
        """Generate decorative elements based on emotion."""
        elements = []
        
        # Add emotion-specific decorations
        if segment.emotion == "excited":
            # Add sparkles or stars
            elements.extend(self._create_sparkle_elements(duration, output_dir))
        elif segment.emotion == "happy":
            # Add confetti or hearts
            elements.extend(self._create_confetti_elements(duration, output_dir))
        elif segment.emotion == "surprised":
            # Add exclamation marks or burst effects
            elements.extend(self._create_burst_elements(duration, output_dir))
        
        return elements
    
    def _create_sparkle_elements(
        self,
        duration: float,
        output_dir: Path
    ) -> List[VisualElement]:
        """Create sparkle decorative elements."""
        elements = []
        
        # Create a few sparkles at random positions
        num_sparkles = random.randint(3, 5)
        
        for i in range(num_sparkles):
            # Create sparkle image
            sparkle_img = self._create_sparkle_image()
            
            # Save sparkle
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sparkle_path = output_dir / f"sparkle_{i}_{timestamp}.png"
            sparkle_img.save(sparkle_path)
            
            # Random position
            x = random.randint(50, self.video_settings.width - 50)
            y = random.randint(50, self.video_settings.height // 2)
            
            # Create element with animation
            sparkle_element = VisualElement(
                type=VisualType.OVERLAY,
                file_path=sparkle_path,
                position=(x, y),
                size=(50, 50),
                duration=duration,
                start_time=random.uniform(0, duration * 0.5),
                end_time=random.uniform(duration * 0.5, duration),
                animation={
                    "type": "twinkle",
                    "frequency": 2.0
                }
            )
            
            elements.append(sparkle_element)
        
        return elements
    
    def _create_sparkle_image(self) -> Image.Image:
        """Create a simple sparkle image."""
        size = 50
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a simple star shape
        center = size // 2
        
        # Draw cross
        draw.line([(center, 0), (center, size)], fill=(255, 255, 200, 255), width=3)
        draw.line([(0, center), (size, center)], fill=(255, 255, 200, 255), width=3)
        
        # Draw diagonal lines
        draw.line([(0, 0), (size, size)], fill=(255, 255, 200, 200), width=2)
        draw.line([(size, 0), (0, size)], fill=(255, 255, 200, 200), width=2)
        
        return image
    
    def _create_confetti_elements(
        self,
        duration: float,
        output_dir: Path
    ) -> List[VisualElement]:
        """Create confetti decorative elements."""
        # Similar to sparkles but with different shapes and colors
        return []  # Simplified for now
    
    def _create_burst_elements(
        self,
        duration: float,
        output_dir: Path
    ) -> List[VisualElement]:
        """Create burst effect elements."""
        # Create exclamation marks or burst effects
        return []  # Simplified for now
    
    @handle_errors("VisualGenerator")
    def create_thumbnail(
        self,
        title: str,
        service_name: str,
        project_id: str
    ) -> Path:
        """Create a thumbnail for the video.
        
        Args:
            title: Video title
            service_name: Service name
            project_id: Project ID
            
        Returns:
            Path to the thumbnail image
        """
        # Create thumbnail at YouTube recommended size
        thumb_width, thumb_height = 1280, 720
        
        # Create base image with gradient
        image = Image.new('RGB', (thumb_width, thumb_height))
        draw = ImageDraw.Draw(image)
        
        # Draw gradient background
        self._draw_vertical_gradient(
            draw,
            thumb_width,
            thumb_height,
            (100, 150, 255),  # Light blue
            (50, 100, 200)    # Darker blue
        )
        
        # Add title text
        font_path = self.fonts.get("title")
        if font_path:
            title_font = ImageFont.truetype(font_path, 60)
            subtitle_font = ImageFont.truetype(font_path, 40)
        else:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # Draw title
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (thumb_width - title_width) // 2
        title_y = thumb_height // 3
        
        # Draw title with outline
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx != 0 or dy != 0:
                    draw.text((title_x + dx, title_y + dy), title, 
                             font=title_font, fill=(0, 0, 0))
        draw.text((title_x, title_y), title, font=title_font, fill=(255, 255, 255))
        
        # Draw service name
        subtitle_bbox = draw.textbbox((0, 0), service_name, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (thumb_width - subtitle_width) // 2
        subtitle_y = title_y + 100
        
        draw.text((subtitle_x, subtitle_y), service_name, 
                 font=subtitle_font, fill=(255, 255, 200))
        
        # Save thumbnail
        thumb_path = self.output_dir / project_id / "thumbnail.png"
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(thumb_path)
        
        self.logger.info(f"Created thumbnail: {thumb_path}")
        
        return thumb_path