"""Video composition module for assembling final YouTube Shorts videos."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import subprocess
import json

try:
    from moviepy.editor import *
    from moviepy.video.fx import resize, fadein, fadeout
    from moviepy.audio.fx import audio_fadein, audio_fadeout
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

from PIL import Image
import numpy as np

from ..models.video import VideoClip, VisualElement, VisualType, VideoSettings
from ..models.audio import AudioClip
from ..models.project import Project
from ..utils import Config, get_logger, handle_errors, dev_error_logger
from ..utils.exceptions import VideoProcessingError


class VideoComposer:
    """Compose final videos from audio and visual elements."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the video composer.
        
        Args:
            config: Configuration object. If not provided, will create default.
        """
        self.config = config or Config()
        self.logger = get_logger(__name__)
        
        # Check for moviepy
        if not HAS_MOVIEPY:
            self.logger.warning("MoviePy not available. Using FFmpeg directly.")
            
        # Get video settings
        self.video_settings = self._get_video_settings()
        
        # Ensure output directory exists
        self.output_dir = self.config.get_output_path(
            self.config.get("output.videos_dir", "videos")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for FFmpeg
        self._check_ffmpeg()
        
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
    
    def _check_ffmpeg(self) -> None:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info("FFmpeg is available")
            self.has_ffmpeg = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("FFmpeg not found. Video composition may be limited.")
            self.has_ffmpeg = False
            
    @handle_errors("VideoComposer")
    def compose_video(
        self,
        audio_clips: List[AudioClip],
        visual_elements: List[List[VisualElement]],
        project: Project,
        add_background_music: bool = False
    ) -> Path:
        """Compose a video from audio clips and visual elements.
        
        Args:
            audio_clips: List of audio clips for each segment
            visual_elements: List of visual elements for each segment
            project: Project object
            add_background_music: Whether to add background music
            
        Returns:
            Path to the composed video file
        """
        self.logger.info(f"Composing video for project {project.id}")
        
        # Create project output directory
        project_dir = self.output_dir / project.id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Choose composition method
        if HAS_MOVIEPY:
            return self._compose_with_moviepy(
                audio_clips,
                visual_elements,
                project,
                project_dir,
                add_background_music
            )
        elif self.has_ffmpeg:
            return self._compose_with_ffmpeg(
                audio_clips,
                visual_elements,
                project,
                project_dir,
                add_background_music
            )
        else:
            raise VideoProcessingError("No video composition method available. "
                                     "Install moviepy or ffmpeg.")
    
    def _compose_with_moviepy(
        self,
        audio_clips: List[AudioClip],
        visual_elements: List[List[VisualElement]],
        project: Project,
        output_dir: Path,
        add_background_music: bool
    ) -> Path:
        """Compose video using MoviePy."""
        try:
            # Create audio track
            audio_track = self._create_audio_track_moviepy(audio_clips)
            
            # Create video track
            video_track = self._create_video_track_moviepy(
                visual_elements,
                audio_clips
            )
            
            # Combine audio and video
            final_video = video_track.set_audio(audio_track)
            
            # Add background music if requested
            if add_background_music:
                final_video = self._add_background_music_moviepy(final_video)
            
            # Add watermark/branding
            final_video = self._add_watermark_moviepy(final_video)
            
            # Export video
            output_path = output_dir / f"{project.name or 'video'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            
            self.logger.info(f"Exporting video to {output_path}")
            
            final_video.write_videofile(
                str(output_path),
                fps=self.video_settings.fps,
                codec=self.video_settings.codec,
                bitrate=self.video_settings.bitrate,
                audio_codec=self.video_settings.audio_codec,
                audio_bitrate=self.video_settings.audio_bitrate,
                preset='medium',
                threads=4
            )
            
            # Clean up
            final_video.close()
            
            self.logger.info(f"Video composed successfully: {output_path}")
            return output_path
            
        except Exception as e:
            dev_error_logger.log_error(
                module="VideoComposer",
                error_type="MoviePyCompositionError",
                description=f"Failed to compose video with MoviePy",
                exception=e
            )
            raise VideoProcessingError(f"Video composition failed: {str(e)}")
    
    def _create_audio_track_moviepy(self, audio_clips: List[AudioClip]) -> Any:
        """Create audio track from audio clips using MoviePy."""
        from moviepy.editor import AudioFileClip, concatenate_audioclips
        
        audio_segments = []
        
        for clip in audio_clips:
            if clip.file_path and clip.file_path.exists():
                audio_segment = AudioFileClip(str(clip.file_path))
                
                # Add fade in/out
                audio_segment = audio_fadein(audio_segment, 0.1)
                audio_segment = audio_fadeout(audio_segment, 0.1)
                
                audio_segments.append(audio_segment)
            else:
                self.logger.warning(f"Audio file not found: {clip.file_path}")
        
        if not audio_segments:
            raise VideoProcessingError("No valid audio clips found")
        
        # Concatenate all audio segments
        return concatenate_audioclips(audio_segments)
    
    def _create_video_track_moviepy(
        self,
        visual_elements: List[List[VisualElement]],
        audio_clips: List[AudioClip]
    ) -> Any:
        """Create video track from visual elements using MoviePy."""
        from moviepy.editor import (
            ImageClip, VideoClip, CompositeVideoClip,
            concatenate_videoclips, TextClip
        )
        
        video_segments = []
        
        # Process each segment
        for i, (segment_visuals, audio_clip) in enumerate(zip(visual_elements, audio_clips)):
            # Get segment duration from audio
            segment_duration = audio_clip.duration
            
            # Find background
            background = None
            overlays = []
            
            for visual in segment_visuals:
                if visual.type == VisualType.BACKGROUND:
                    # Create background clip
                    if visual.file_path and visual.file_path.exists():
                        background = ImageClip(str(visual.file_path))
                        background = background.set_duration(segment_duration)
                        background = background.resize(self.video_settings.resolution)
                else:
                    # Create overlay clips
                    overlay = self._create_overlay_clip_moviepy(visual, segment_duration)
                    if overlay:
                        overlays.append(overlay)
            
            # Create default background if none exists
            if background is None:
                background = self._create_default_background_moviepy(segment_duration)
            
            # Composite all elements
            if overlays:
                segment_video = CompositeVideoClip([background] + overlays)
            else:
                segment_video = background
            
            # Add transitions
            if i > 0:
                segment_video = fadein(segment_video, 0.3)
            if i < len(visual_elements) - 1:
                segment_video = fadeout(segment_video, 0.3)
            
            video_segments.append(segment_video)
        
        # Concatenate all segments
        return concatenate_videoclips(video_segments, method="compose")
    
    def _create_overlay_clip_moviepy(
        self,
        visual: VisualElement,
        segment_duration: float
    ) -> Optional[Any]:
        """Create an overlay clip from visual element."""
        from moviepy.editor import ImageClip, TextClip
        
        try:
            if visual.type == VisualType.TEXT and visual.file_path and visual.file_path.exists():
                # Create image clip from text image
                clip = ImageClip(str(visual.file_path))
                
                # Set duration and position
                clip = clip.set_duration(visual.duration)
                clip = clip.set_position(visual.position)
                clip = clip.set_start(visual.start_time)
                
                # Apply animation
                if visual.animation:
                    clip = self._apply_animation_moviepy(clip, visual.animation)
                
                return clip
                
            elif visual.type == VisualType.OVERLAY and visual.file_path and visual.file_path.exists():
                # Create overlay clip
                clip = ImageClip(str(visual.file_path))
                clip = clip.set_duration(visual.duration)
                clip = clip.set_position(visual.position)
                clip = clip.set_start(visual.start_time)
                
                return clip
                
        except Exception as e:
            self.logger.error(f"Failed to create overlay clip: {e}")
            return None
    
    def _apply_animation_moviepy(self, clip: Any, animation: Dict[str, Any]) -> Any:
        """Apply animation to a clip."""
        from moviepy.editor import fadein, fadeout
        
        anim_type = animation.get("type", "none")
        
        if anim_type == "fade_in_out":
            in_duration = animation.get("in_duration", 0.3)
            out_duration = animation.get("out_duration", 0.3)
            clip = fadein(clip, in_duration)
            clip = fadeout(clip, out_duration)
        elif anim_type == "twinkle":
            # Create twinkle effect by modulating opacity
            frequency = animation.get("frequency", 2.0)
            clip = clip.fl(lambda gf, t: gf(t).astype('float') * 
                          (0.5 + 0.5 * np.sin(2 * np.pi * frequency * t)),
                          apply_to=['mask'])
        
        return clip
    
    def _create_default_background_moviepy(self, duration: float) -> Any:
        """Create a default background clip."""
        from moviepy.editor import ColorClip
        
        # Create a simple gradient background
        width, height = self.video_settings.resolution
        
        # Create color clip
        background = ColorClip(
            size=(width, height),
            color=(64, 64, 128),  # Dark blue-gray
            duration=duration
        )
        
        return background
    
    def _add_background_music_moviepy(self, video: Any) -> Any:
        """Add background music to video."""
        try:
            from moviepy.editor import AudioFileClip, CompositeAudioClip
            
            # Check if we have background music
            music_path = self.assets_dir / "music" / "background.mp3"
            if not music_path.exists():
                self.logger.info("No background music found")
                return video
            
            # Load background music
            music = AudioFileClip(str(music_path))
            
            # Loop if necessary
            if music.duration < video.duration:
                music = music.loop(duration=video.duration)
            else:
                music = music.subclip(0, video.duration)
            
            # Reduce volume
            music = music.volumex(0.1)  # 10% volume
            
            # Mix with original audio
            if video.audio:
                mixed_audio = CompositeAudioClip([video.audio, music])
                video = video.set_audio(mixed_audio)
            else:
                video = video.set_audio(music)
            
            return video
            
        except Exception as e:
            self.logger.warning(f"Failed to add background music: {e}")
            return video
    
    def _add_watermark_moviepy(self, video: Any) -> Any:
        """Add watermark or branding to video."""
        try:
            from moviepy.editor import TextClip, CompositeVideoClip
            
            # Create watermark text
            watermark = TextClip(
                "Generated by AI",
                fontsize=20,
                color='white',
                font='Arial',
                stroke_color='black',
                stroke_width=1
            )
            
            # Position at bottom right
            watermark = watermark.set_position(('right', 'bottom'))
            watermark = watermark.set_duration(video.duration)
            watermark = watermark.set_opacity(0.5)
            
            # Composite with video
            return CompositeVideoClip([video, watermark])
            
        except Exception as e:
            self.logger.warning(f"Failed to add watermark: {e}")
            return video
    
    def _compose_with_ffmpeg(
        self,
        audio_clips: List[AudioClip],
        visual_elements: List[List[VisualElement]],
        project: Project,
        output_dir: Path,
        add_background_music: bool
    ) -> Path:
        """Compose video using FFmpeg directly."""
        try:
            # Create temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Concatenate audio files
                audio_list_file = temp_path / "audio_list.txt"
                self._create_audio_concat_list(audio_clips, audio_list_file)
                
                combined_audio = temp_path / "combined_audio.mp3"
                self._concatenate_audio_ffmpeg(audio_list_file, combined_audio)
                
                # Create video segments
                video_segments = []
                for i, (segment_visuals, audio_clip) in enumerate(zip(visual_elements, audio_clips)):
                    segment_video = self._create_segment_video_ffmpeg(
                        segment_visuals,
                        audio_clip.duration,
                        temp_path / f"segment_{i}.mp4",
                        i
                    )
                    if segment_video:
                        video_segments.append(segment_video)
                
                # Concatenate video segments
                if not video_segments:
                    raise VideoProcessingError("No video segments created")
                
                video_list_file = temp_path / "video_list.txt"
                self._create_video_concat_list(video_segments, video_list_file)
                
                # Create final output path
                output_path = output_dir / f"{project.name or 'video'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                
                # Combine everything
                self._create_final_video_ffmpeg(
                    video_list_file,
                    combined_audio,
                    output_path,
                    add_background_music
                )
                
                self.logger.info(f"Video composed successfully: {output_path}")
                return output_path
                
        except Exception as e:
            dev_error_logger.log_error(
                module="VideoComposer",
                error_type="FFmpegCompositionError",
                description=f"Failed to compose video with FFmpeg",
                exception=e
            )
            raise VideoProcessingError(f"FFmpeg composition failed: {str(e)}")
    
    def _create_audio_concat_list(
        self,
        audio_clips: List[AudioClip],
        output_path: Path
    ) -> None:
        """Create concat list for audio files."""
        with open(output_path, 'w') as f:
            for clip in audio_clips:
                if clip.file_path and clip.file_path.exists():
                    f.write(f"file '{clip.file_path.absolute()}'\n")
    
    def _concatenate_audio_ffmpeg(
        self,
        list_file: Path,
        output_path: Path
    ) -> None:
        """Concatenate audio files using FFmpeg."""
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-y",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise VideoProcessingError(f"Audio concatenation failed: {result.stderr}")
    
    def _create_segment_video_ffmpeg(
        self,
        visuals: List[VisualElement],
        duration: float,
        output_path: Path,
        segment_index: int
    ) -> Optional[Path]:
        """Create a video segment using FFmpeg."""
        # Find background
        background = None
        for visual in visuals:
            if visual.type == VisualType.BACKGROUND and visual.file_path and visual.file_path.exists():
                background = visual.file_path
                break
        
        if not background:
            # Create default background
            background = self._create_default_background_ffmpeg(duration, output_path.parent)
        
        # Create video from background image
        cmd = [
            "ffmpeg",
            "-loop", "1",
            "-i", str(background),
            "-c:v", self.video_settings.codec,
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={self.video_settings.width}:{self.video_settings.height}",
            "-y",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.error(f"Segment video creation failed: {result.stderr}")
            return None
            
        return output_path
    
    def _create_default_background_ffmpeg(
        self,
        duration: float,
        output_dir: Path
    ) -> Path:
        """Create a default background using FFmpeg."""
        output_path = output_dir / "default_bg.png"
        
        # Create a simple color background
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"color=c=navy:s={self.video_settings.width}x{self.video_settings.height}",
            "-frames:v", "1",
            "-y",
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    
    def _create_video_concat_list(
        self,
        video_segments: List[Path],
        output_path: Path
    ) -> None:
        """Create concat list for video files."""
        with open(output_path, 'w') as f:
            for segment in video_segments:
                f.write(f"file '{segment.absolute()}'\n")
    
    def _create_final_video_ffmpeg(
        self,
        video_list: Path,
        audio_path: Path,
        output_path: Path,
        add_background_music: bool
    ) -> None:
        """Create final video with audio using FFmpeg."""
        # Base command
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(video_list),
            "-i", str(audio_path),
            "-c:v", self.video_settings.codec,
            "-c:a", self.video_settings.audio_codec,
            "-b:v", self.video_settings.bitrate,
            "-b:a", self.video_settings.audio_bitrate,
            "-shortest",
            "-y",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise VideoProcessingError(f"Final video creation failed: {result.stderr}")
    
    @handle_errors("VideoComposer")
    def add_subtitles(
        self,
        video_path: Path,
        subtitles: List[Dict[str, Any]],
        output_path: Optional[Path] = None
    ) -> Path:
        """Add subtitles to a video.
        
        Args:
            video_path: Path to the video file
            subtitles: List of subtitle entries with text, start, and end times
            output_path: Optional output path. If not provided, creates new file
            
        Returns:
            Path to the video with subtitles
        """
        if not output_path:
            output_path = video_path.parent / f"{video_path.stem}_subtitled{video_path.suffix}"
        
        # Create SRT file
        srt_path = video_path.parent / f"{video_path.stem}.srt"
        self._create_srt_file(subtitles, srt_path)
        
        # Add subtitles using FFmpeg
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vf", f"subtitles={srt_path}:force_style='FontName=Arial,FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2'",
            "-c:a", "copy",
            "-y",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise VideoProcessingError(f"Subtitle addition failed: {result.stderr}")
        
        # Clean up SRT file
        srt_path.unlink()
        
        return output_path
    
    def _create_srt_file(
        self,
        subtitles: List[Dict[str, Any]],
        output_path: Path
    ) -> None:
        """Create an SRT subtitle file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, subtitle in enumerate(subtitles, 1):
                # Write subtitle number
                f.write(f"{i}\n")
                
                # Write timecode
                start_time = self._seconds_to_srt_time(subtitle['start'])
                end_time = self._seconds_to_srt_time(subtitle['end'])
                f.write(f"{start_time} --> {end_time}\n")
                
                # Write text
                f.write(f"{subtitle['text']}\n\n")
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    @property
    def assets_dir(self) -> Path:
        """Get assets directory path."""
        return Path("assets")