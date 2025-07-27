"""Main orchestrator for YouTube Shorts Generator."""

import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from .models.project import Project, ProjectStatus, VideoMetadata
from .models.script import ScriptStyle
from .modules.script_generator import ScriptGenerator
from .modules.script_processor import ScriptProcessor
from .modules.voice_synthesizer import VoiceSynthesizer
from .modules.visual_generator import VisualGenerator
from .modules.video_composer import VideoComposer
from .modules.social_media_manager import SocialMediaManager
from .utils import Config, setup_logger, get_logger, dev_error_logger
from .utils.exceptions import YouTubeShortsGeneratorError


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
    
    # Module-specific test methods
    def test_script_generation(self, service_name: str, affiliate_url: str, 
                              style: str = "humorous") -> Dict[str, Any]:
        """Test only script generation module."""
        try:
            self.logger.info("Testing script generation module...")
            
            # Generate script
            script_style = ScriptStyle[style.upper()]
            script = self.script_generator.generate_script(
                service_name=service_name,
                affiliate_url=affiliate_url,
                style=script_style,
                target_duration=self.config.get("video.max_duration", 60)
            )
            
            # Save script
            output_dir = self.config.get_output_path("scripts")
            output_dir.mkdir(parents=True, exist_ok=True)
            script_file = output_dir / f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(script_file, 'w', encoding='utf-8') as f:
                json.dump(script.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Script saved to: {script_file}")
            
            return {
                'success': True,
                'script': script,
                'script_file': str(script_file),
                'segments': len(script.segments),
                'duration': script.total_duration
            }
            
        except Exception as e:
            self.logger.error(f"Script generation test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_script_processing(self, script_file: str) -> Dict[str, Any]:
        """Test only script processing module."""
        try:
            self.logger.info("Testing script processing module...")
            
            # Load script
            with open(script_file, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            # Recreate script object
            from .models.script import Script
            script = Script.from_dict(script_data)
            
            # Process script
            processed = self.script_processor.process_script(script)
            segments = self.script_processor.export_for_tts(processed)
            
            # Save processed segments
            output_dir = self.config.get_output_path("scripts")
            output_file = output_dir / f"processed_{Path(script_file).stem}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(segments, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Processed segments saved to: {output_file}")
            
            return {
                'success': True,
                'processed_file': str(output_file),
                'segments': len(segments),
                'total_duration': sum(s['duration'] for s in segments)
            }
            
        except Exception as e:
            self.logger.error(f"Script processing test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_voice_synthesis(self, segments_file: str) -> Dict[str, Any]:
        """Test only voice synthesis module."""
        try:
            self.logger.info("Testing voice synthesis module...")
            
            # Load segments
            with open(segments_file, 'r', encoding='utf-8') as f:
                segments = json.load(f)
            
            # Generate audio for each segment
            project_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            audio_clips = self.voice_synthesizer.synthesize_script(segments, project_id)
            
            # Save audio info
            output_dir = self.config.get_output_path("audio") / project_id
            info_file = output_dir / "audio_info.json"
            
            audio_info = [
                {
                    'segment_id': clip.segment_id,
                    'file_path': str(clip.file_path),
                    'duration': clip.duration
                }
                for clip in audio_clips
            ]
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(audio_info, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Audio info saved to: {info_file}")
            
            return {
                'success': True,
                'audio_clips': len(audio_clips),
                'total_duration': sum(clip.duration for clip in audio_clips),
                'audio_dir': str(output_dir),
                'info_file': str(info_file)
            }
            
        except Exception as e:
            self.logger.error(f"Voice synthesis test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_visual_generation(self, segments_file: str) -> Dict[str, Any]:
        """Test only visual generation module."""
        try:
            self.logger.info("Testing visual generation module...")
            
            # Load segments
            with open(segments_file, 'r', encoding='utf-8') as f:
                segments_data = json.load(f)
            
            # Generate visuals for each segment
            project_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            all_visuals = []
            
            for seg_data in segments_data:
                # Create segment object
                from .models.script import ScriptSegment
                segment = ScriptSegment(
                    id=seg_data["id"],
                    text=seg_data["text"],
                    duration=seg_data["duration"],
                    emotion=seg_data.get("emotion", "neutral"),
                    emphasis_words=seg_data.get("emphasis_words", [])
                )
                
                visuals = self.visual_generator.generate_segment_visuals(
                    segment, segment.duration, project_id
                )
                all_visuals.append(visuals)
            
            # Save visual info
            output_dir = self.config.get_output_path("visuals") / project_id
            info_file = output_dir / "visual_info.json"
            
            visual_info = [
                [
                    {
                        'type': v.type.value,
                        'file_path': str(v.file_path),
                        'duration': v.duration
                    }
                    for v in segment_visuals
                ]
                for segment_visuals in all_visuals
            ]
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(visual_info, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Visual info saved to: {info_file}")
            
            return {
                'success': True,
                'segments': len(all_visuals),
                'total_visuals': sum(len(v) for v in all_visuals),
                'visual_dir': str(output_dir),
                'info_file': str(info_file)
            }
            
        except Exception as e:
            self.logger.error(f"Visual generation test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_video_composition(self, audio_dir: str, visual_dir: str) -> Dict[str, Any]:
        """Test only video composition module."""
        try:
            self.logger.info("Testing video composition module...")
            
            # Load audio and visual info
            audio_info_file = Path(audio_dir) / "audio_info.json"
            visual_info_file = Path(visual_dir) / "visual_info.json"
            
            with open(audio_info_file, 'r') as f:
                audio_info = json.load(f)
            
            with open(visual_info_file, 'r') as f:
                visual_info = json.load(f)
            
            # Create audio clips and visual elements
            from .models.audio import AudioClip
            from .models.video import VisualElement, VisualType
            
            audio_clips = [
                AudioClip(
                    segment_id=info['segment_id'],
                    text="",  # Not needed for composition
                    file_path=Path(info['file_path']),
                    duration=info['duration']
                )
                for info in audio_info
            ]
            
            visual_elements = [
                [
                    VisualElement(
                        type=VisualType(v['type']),
                        file_path=Path(v['file_path']),
                        duration=v['duration']
                    )
                    for v in segment_visuals
                ]
                for segment_visuals in visual_info
            ]
            
            # Create project
            project = Project(
                service_name="Test Video",
                affiliate_url="https://example.com"
            )
            
            # Compose video
            video_path = self.video_composer.compose_video(
                audio_clips, visual_elements, project
            )
            
            self.logger.info(f"Video saved to: {video_path}")
            
            return {
                'success': True,
                'video_path': str(video_path),
                'duration': sum(clip.duration for clip in audio_clips)
            }
            
        except Exception as e:
            self.logger.error(f"Video composition test failed: {e}")
            return {'success': False, 'error': str(e)}
    
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
    
    # Module testing arguments
    parser.add_argument(
        "--test-module",
        choices=["script-gen", "script-proc", "voice", "visual", "video", "social"],
        help="Test a specific module"
    )
    parser.add_argument(
        "--script-file",
        help="Path to script file (for script-proc, voice, visual tests)"
    )
    parser.add_argument(
        "--segments-file",
        help="Path to processed segments file (for voice, visual tests)"
    )
    parser.add_argument(
        "--audio-dir",
        help="Path to audio directory (for video test)"
    )
    parser.add_argument(
        "--visual-dir",
        help="Path to visual directory (for video test)"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize generator
        generator = YouTubeShortsGenerator(args.config)
        
        # Set output directory if specified
        if args.output_dir:
            generator.config.set("output.base_dir", args.output_dir)
        
        # Handle module testing
        if args.test_module:
            if args.test_module == "script-gen":
                result = generator.test_script_generation(
                    args.service, args.url, args.style
                )
                if result['success']:
                    print(f"✓ Script generation test successful!")
                    print(f"  Script file: {result['script_file']}")
                    print(f"  Segments: {result['segments']}")
                    print(f"  Duration: {result['duration']:.1f}s")
                else:
                    print(f"✗ Script generation test failed: {result['error']}")
                    sys.exit(1)
                    
            elif args.test_module == "script-proc":
                if not args.script_file:
                    print("✗ --script-file required for script processing test")
                    sys.exit(1)
                result = generator.test_script_processing(args.script_file)
                if result['success']:
                    print(f"✓ Script processing test successful!")
                    print(f"  Processed file: {result['processed_file']}")
                    print(f"  Segments: {result['segments']}")
                    print(f"  Duration: {result['total_duration']:.1f}s")
                else:
                    print(f"✗ Script processing test failed: {result['error']}")
                    sys.exit(1)
                    
            elif args.test_module == "voice":
                if not args.segments_file:
                    print("✗ --segments-file required for voice synthesis test")
                    sys.exit(1)
                result = generator.test_voice_synthesis(args.segments_file)
                if result['success']:
                    print(f"✓ Voice synthesis test successful!")
                    print(f"  Audio clips: {result['audio_clips']}")
                    print(f"  Duration: {result['total_duration']:.1f}s")
                    print(f"  Audio dir: {result['audio_dir']}")
                else:
                    print(f"✗ Voice synthesis test failed: {result['error']}")
                    sys.exit(1)
                    
            elif args.test_module == "visual":
                if not args.segments_file:
                    print("✗ --segments-file required for visual generation test")
                    sys.exit(1)
                result = generator.test_visual_generation(args.segments_file)
                if result['success']:
                    print(f"✓ Visual generation test successful!")
                    print(f"  Segments: {result['segments']}")
                    print(f"  Total visuals: {result['total_visuals']}")
                    print(f"  Visual dir: {result['visual_dir']}")
                else:
                    print(f"✗ Visual generation test failed: {result['error']}")
                    sys.exit(1)
                    
            elif args.test_module == "video":
                if not args.audio_dir or not args.visual_dir:
                    print("✗ --audio-dir and --visual-dir required for video composition test")
                    sys.exit(1)
                result = generator.test_video_composition(args.audio_dir, args.visual_dir)
                if result['success']:
                    print(f"✓ Video composition test successful!")
                    print(f"  Video path: {result['video_path']}")
                    print(f"  Duration: {result['duration']:.1f}s")
                else:
                    print(f"✗ Video composition test failed: {result['error']}")
                    sys.exit(1)
                    
            elif args.test_module == "social":
                print("✗ Social media test not implemented yet")
                sys.exit(1)
            
            # Exit after module test
            sys.exit(0)
        
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