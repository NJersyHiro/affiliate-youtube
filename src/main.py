"""Main orchestrator for YouTube Shorts Generator."""

import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from models.project import Project, ProjectStatus, VideoMetadata
from models.script import ScriptStyle
from modules.script_generator import ScriptGenerator
from modules.script_processor import ScriptProcessor
from modules.voice_synthesizer import VoiceSynthesizer
from modules.visual_generator import VisualGenerator
from modules.video_composer import VideoComposer
from modules.social_media_manager import SocialMediaManager
from utils import Config, setup_logger, get_logger, dev_error_logger
from utils.exceptions import YouTubeShortsGeneratorError


class YouTubeShortsGenerator:
    """Main orchestrator for generating YouTube Shorts."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the generator.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Initialize configuration
        self.config = Config(config_path)
        
        # Set up logging
        log_level = self.config.get("logging.level", "INFO")
        log_file = self.config.get("logging.file")
        self.logger = setup_logger(level=log_level, log_file=log_file)
        
        # Ensure output directories exist
        self.config.ensure_output_dirs()
        
        # Initialize modules
        self._init_modules()
        
        self.logger.info("YouTube Shorts Generator initialized")
        
    def _init_modules(self) -> None:
        """Initialize all modules."""
        try:
            self.script_generator = ScriptGenerator(self.config)
            self.script_processor = ScriptProcessor(self.config)
            self.voice_synthesizer = VoiceSynthesizer(self.config)
            self.visual_generator = VisualGenerator(self.config)
            self.video_composer = VideoComposer(self.config)
            self.social_media_manager = SocialMediaManager(self.config)
            
            self.logger.info("All modules initialized successfully")
            
        except Exception as e:
            dev_error_logger.log_error(
                module="Main",
                error_type="ModuleInitError",
                description="Failed to initialize modules",
                exception=e
            )
            raise
    
    def create_and_post(
        self,
        service_name: str,
        affiliate_url: str,
        style: str = "humorous",
        auto_post: bool = False,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create and optionally post a YouTube Short.
        
        Args:
            service_name: Name of the service to promote
            affiliate_url: Affiliate URL
            style: Script style (humorous, educational, storytelling, etc.)
            auto_post: Whether to automatically post to YouTube
            project_name: Optional project name
            
        Returns:
            Dictionary with results
        """
        # Create project
        project = Project(
            name=project_name or f"{service_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            service_name=service_name,
            affiliate_url=affiliate_url
        )
        
        try:
            # Phase 1: Generate script
            self.logger.info("Phase 1: Generating script...")
            script_style = ScriptStyle[style.upper()] if isinstance(style, str) else style
            
            script = self.script_generator.generate_script(
                service_name=service_name,
                affiliate_url=affiliate_url,
                style=script_style
            )
            
            project.script = script
            project.update_status(ProjectStatus.SCRIPT_GENERATED)
            self.logger.info(f"Script generated: {len(script.segments)} segments, "
                           f"{script.total_duration:.1f}s total")
            
            # Phase 2: Process script
            self.logger.info("Phase 2: Processing script...")
            processed_script = self.script_processor.process_script(script)
            tts_segments = self.script_processor.export_for_tts(processed_script)
            
            project.script = processed_script
            self.logger.info("Script processed and optimized for TTS")
            
            # Phase 3: Generate audio
            self.logger.info("Phase 3: Synthesizing audio...")
            audio_clips = self.voice_synthesizer.synthesize_script(
                tts_segments,
                project.id
            )
            
            for clip in audio_clips:
                project.add_audio_clip(clip)
                
            project.update_status(ProjectStatus.AUDIO_GENERATED)
            self.logger.info(f"Audio generated: {len(audio_clips)} clips")
            
            # Phase 4: Generate visuals
            self.logger.info("Phase 4: Generating visuals...")
            visual_elements = []
            
            for segment, audio_clip in zip(processed_script.segments, audio_clips):
                segment_visuals = self.visual_generator.generate_segment_visuals(
                    segment,
                    audio_clip.duration,
                    project.id
                )
                visual_elements.append(segment_visuals)
            
            # Generate thumbnail
            thumbnail_path = self.visual_generator.create_thumbnail(
                title=processed_script.title,
                service_name=service_name,
                project_id=project.id
            )
            
            project.video_metadata.thumbnail_path = thumbnail_path
            project.update_status(ProjectStatus.VISUALS_GENERATED)
            self.logger.info(f"Visuals generated for {len(visual_elements)} segments")
            
            # Phase 5: Compose video
            self.logger.info("Phase 5: Composing video...")
            video_path = self.video_composer.compose_video(
                audio_clips=audio_clips,
                visual_elements=visual_elements,
                project=project,
                add_background_music=self.config.get("video.add_background_music", False)
            )
            
            project.final_video_path = video_path
            project.update_status(ProjectStatus.VIDEO_COMPOSED)
            self.logger.info(f"Video composed: {video_path}")
            
            # Update video metadata
            project.video_metadata = VideoMetadata(
                title=script.title,
                description=script.description,
                tags=script.tags,
                thumbnail_path=thumbnail_path
            )
            
            project.update_status(ProjectStatus.READY_TO_UPLOAD)
            
            # Phase 6: Upload to YouTube (if requested)
            upload_result = None
            if auto_post:
                self.logger.info("Phase 6: Uploading to YouTube...")
                upload_result = self.social_media_manager.upload_to_youtube(
                    video_path=video_path,
                    project=project,
                    thumbnail_path=thumbnail_path
                )
                
                if upload_result.get('success'):
                    self.logger.info(f"Video uploaded: {upload_result['video_url']}")
                else:
                    self.logger.error(f"Upload failed: {upload_result.get('error')}")
            
            # Save project
            project_file = project.save_to_file()
            self.logger.info(f"Project saved to: {project_file}")
            
            return {
                'success': True,
                'project': project,
                'video_path': str(video_path),
                'upload_result': upload_result,
                'project_file': str(project_file)
            }
            
        except Exception as e:
            dev_error_logger.log_error(
                module="Main",
                error_type="GenerationError",
                description=f"Failed to generate video for {service_name}",
                exception=e
            )
            
            project.update_status(ProjectStatus.FAILED)
            
            return {
                'success': False,
                'error': str(e),
                'project': project
            }
    
    def batch_create(
        self,
        services: List[Dict[str, str]],
        default_style: str = "humorous",
        auto_post: bool = False,
        schedule_start: Optional[datetime] = None,
        interval_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Create multiple videos in batch.
        
        Args:
            services: List of dicts with 'name' and 'url' keys
            default_style: Default style for all videos
            auto_post: Whether to auto-post videos
            schedule_start: Start time for scheduled posting
            interval_hours: Hours between scheduled posts
            
        Returns:
            List of results for each video
        """
        results = []
        projects = []
        
        for service in services:
            self.logger.info(f"\nProcessing: {service['name']}")
            
            result = self.create_and_post(
                service_name=service['name'],
                affiliate_url=service['url'],
                style=service.get('style', default_style),
                auto_post=False  # Don't auto-post individually
            )
            
            results.append(result)
            
            if result['success']:
                projects.append(result['project'])
        
        # Schedule uploads if requested
        if auto_post and projects and schedule_start:
            self.logger.info("\nScheduling uploads...")
            upload_results = self.social_media_manager.schedule_uploads(
                projects=projects,
                start_time=schedule_start,
                interval_hours=interval_hours
            )
            
            # Add upload results to main results
            for result, upload_result in zip(results, upload_results):
                if result['success']:
                    result['upload_result'] = upload_result
        
        return results
    
    def resume_project(self, project_file: str) -> Dict[str, Any]:
        """Resume a failed or incomplete project.
        
        Args:
            project_file: Path to saved project file
            
        Returns:
            Dictionary with results
        """
        try:
            # Load project
            project = Project.load_from_file(Path(project_file))
            self.logger.info(f"Loaded project: {project.name}, status: {project.status.value}")
            
            # Determine where to resume
            if project.status == ProjectStatus.DRAFT:
                # Start from beginning
                return self.create_and_post(
                    service_name=project.service_name,
                    affiliate_url=project.affiliate_url,
                    project_name=project.name
                )
            
            elif project.status == ProjectStatus.READY_TO_UPLOAD:
                # Just upload
                if project.final_video_path and project.final_video_path.exists():
                    upload_result = self.social_media_manager.upload_to_youtube(
                        video_path=project.final_video_path,
                        project=project,
                        thumbnail_path=project.video_metadata.thumbnail_path
                    )
                    
                    return {
                        'success': upload_result.get('success', False),
                        'project': project,
                        'upload_result': upload_result
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Video file not found',
                        'project': project
                    }
            
            else:
                # TODO: Implement resuming from intermediate states
                return {
                    'success': False,
                    'error': f'Cannot resume from status: {project.status.value}',
                    'project': project
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to resume project: {str(e)}'
            }


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate YouTube Shorts for affiliate marketing"
    )
    
    # Basic arguments
    parser.add_argument(
        "service",
        help="Service name to promote"
    )
    parser.add_argument(
        "url",
        help="Affiliate URL"
    )
    
    # Optional arguments
    parser.add_argument(
        "--style",
        choices=["humorous", "educational", "storytelling", "comparison", "review"],
        default="humorous",
        help="Script style (default: humorous)"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--auto-post",
        action="store_true",
        help="Automatically post to YouTube"
    )
    parser.add_argument(
        "--project-name",
        help="Project name"
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory"
    )
    
    # Batch processing
    parser.add_argument(
        "--batch",
        help="Path to JSON file with multiple services"
    )
    parser.add_argument(
        "--schedule-start",
        help="Schedule start time (ISO format)"
    )
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=24,
        help="Hours between scheduled posts (default: 24)"
    )
    
    # Resume project
    parser.add_argument(
        "--resume",
        help="Resume from saved project file"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize generator
        generator = YouTubeShortsGenerator(args.config)
        
        # Set output directory if specified
        if args.output_dir:
            generator.config.set("output.base_dir", args.output_dir)
        
        # Handle resume
        if args.resume:
            result = generator.resume_project(args.resume)
            if result['success']:
                print(f"✓ Project resumed successfully!")
                if result.get('upload_result', {}).get('success'):
                    print(f"  Video URL: {result['upload_result']['video_url']}")
            else:
                print(f"✗ Resume failed: {result['error']}")
                sys.exit(1)
        
        # Handle batch processing
        elif args.batch:
            with open(args.batch, 'r', encoding='utf-8') as f:
                services = json.load(f)
            
            schedule_start = None
            if args.schedule_start:
                schedule_start = datetime.fromisoformat(args.schedule_start)
            
            results = generator.batch_create(
                services=services,
                auto_post=args.auto_post,
                schedule_start=schedule_start,
                interval_hours=args.interval_hours
            )
            
            # Print summary
            successful = sum(1 for r in results if r['success'])
            print(f"\nBatch processing complete: {successful}/{len(results)} successful")
            
            for i, result in enumerate(results):
                service_name = services[i]['name']
                if result['success']:
                    print(f"✓ {service_name}: {result['video_path']}")
                else:
                    print(f"✗ {service_name}: {result['error']}")
        
        # Handle single video
        else:
            result = generator.create_and_post(
                service_name=args.service,
                affiliate_url=args.url,
                style=args.style,
                auto_post=args.auto_post,
                project_name=args.project_name
            )
            
            if result['success']:
                print(f"✓ Video created successfully!")
                print(f"  Path: {result['video_path']}")
                print(f"  Project: {result['project_file']}")
                
                if result.get('upload_result', {}).get('success'):
                    print(f"  YouTube: {result['upload_result']['video_url']}")
            else:
                print(f"✗ Video creation failed: {result['error']}")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()