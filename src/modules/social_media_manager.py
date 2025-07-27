"""Social media management module for YouTube Shorts uploads and posting."""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import pickle
import mimetypes

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

from ..models.project import Project, VideoMetadata, ProjectStatus
from ..utils import Config, get_logger, handle_errors, dev_error_logger
from ..utils.exceptions import UploadError, ConfigurationError


class SocialMediaManager:
    """Manage social media uploads and posting, primarily YouTube."""
    
    # YouTube API scopes
    YOUTUBE_SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtubepartner"
    ]
    
    # YouTube Shorts requirements
    SHORTS_MAX_DURATION = 60  # seconds
    SHORTS_ASPECT_RATIO = 9/16  # vertical video
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the social media manager.
        
        Args:
            config: Configuration object. If not provided, will create default.
        """
        self.config = config or Config()
        self.logger = get_logger(__name__)
        
        if not HAS_GOOGLE_API:
            raise ConfigurationError("Google API client not installed. "
                                   "Install with: pip install google-api-python-client google-auth-oauthlib")
        
        # Initialize YouTube service
        self.youtube_service = None
        self._init_youtube_service()
        
        # Get upload settings
        self.upload_settings = self._get_upload_settings()
        
    def _get_upload_settings(self) -> Dict[str, Any]:
        """Get upload settings from config."""
        return {
            "privacy_status": self.config.get("youtube.privacy_status", "private"),
            "made_for_kids": self.config.get("youtube.made_for_kids", False),
            "category_id": self.config.get("youtube.category_id", "22"),  # People & Blogs
            "default_language": self.config.get("youtube.default_language", "ja"),
            "notify_subscribers": self.config.get("youtube.notify_subscribers", True),
            "auto_publish": self.config.get("youtube.auto_publish", False),
            "tags_limit": self.config.get("youtube.tags_limit", 500),  # Character limit for tags
            "title_limit": self.config.get("youtube.title_limit", 100),
            "description_limit": self.config.get("youtube.description_limit", 5000)
        }
    
    def _init_youtube_service(self) -> None:
        """Initialize YouTube API service."""
        try:
            credentials = self._get_youtube_credentials()
            if credentials:
                self.youtube_service = build('youtube', 'v3', credentials=credentials)
                self.logger.info("YouTube API service initialized")
            else:
                self.logger.warning("YouTube credentials not available")
                
        except Exception as e:
            dev_error_logger.log_error(
                module="SocialMediaManager",
                error_type="YouTubeInitError",
                description="Failed to initialize YouTube API service",
                exception=e
            )
            self.logger.error(f"Failed to initialize YouTube service: {e}")
    
    def _get_youtube_credentials(self) -> Optional[Credentials]:
        """Get YouTube API credentials."""
        creds = None
        token_path = Path("config/youtube_token.pickle")
        credentials_path = Path("config/youtube_credentials.json")
        
        # Check for existing token
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                self.logger.info("Loaded existing YouTube token")
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info("Refreshed YouTube token")
                except Exception as e:
                    self.logger.error(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds and credentials_path.exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_path),
                        self.YOUTUBE_SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    self.logger.info("Obtained new YouTube credentials")
                except Exception as e:
                    self.logger.error(f"Failed to authenticate: {e}")
                    return None
            
            # Save the credentials for the next run
            if creds:
                token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
        
        return creds
    
    @handle_errors("SocialMediaManager")
    def upload_to_youtube(
        self,
        video_path: Path,
        project: Project,
        thumbnail_path: Optional[Path] = None,
        schedule_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Upload a video to YouTube as a Short.
        
        Args:
            video_path: Path to the video file
            project: Project object with metadata
            thumbnail_path: Optional thumbnail image
            schedule_time: Optional scheduled publish time
            
        Returns:
            Dictionary with upload results including video ID
        """
        if not self.youtube_service:
            raise UploadError("YouTube service not initialized")
        
        if not video_path.exists():
            raise UploadError(f"Video file not found: {video_path}")
        
        # Validate video is suitable for Shorts
        if not self._validate_shorts_video(video_path):
            raise UploadError("Video does not meet YouTube Shorts requirements")
        
        # Prepare metadata
        metadata = self._prepare_youtube_metadata(project, schedule_time)
        
        try:
            # Create video resource
            body = {
                'snippet': {
                    'title': metadata['title'],
                    'description': metadata['description'],
                    'tags': metadata['tags'],
                    'categoryId': metadata['category_id'],
                    'defaultLanguage': metadata['default_language'],
                    'defaultAudioLanguage': metadata['default_language']
                },
                'status': {
                    'privacyStatus': metadata['privacy_status'],
                    'selfDeclaredMadeForKids': metadata['made_for_kids'],
                    'notifySubscribers': metadata['notify_subscribers']
                }
            }
            
            # Add scheduled time if provided
            if schedule_time and metadata['privacy_status'] == 'private':
                body['status']['publishAt'] = schedule_time.isoformat() + 'Z'
                body['status']['privacyStatus'] = 'private'
            
            # Create media upload
            media = MediaFileUpload(
                str(video_path),
                mimetype='video/mp4',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            # Execute upload
            self.logger.info(f"Uploading video: {video_path}")
            
            request = self.youtube_service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute with resumable upload
            response = None
            error = None
            retry = 0
            
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        self.logger.info(f"Upload progress: {progress}%")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        # Retry on server errors
                        error = f"Server error: {e}"
                        retry += 1
                        if retry > 5:
                            raise UploadError(f"Upload failed after 5 retries: {error}")
                        time.sleep(2 ** retry)
                    else:
                        raise UploadError(f"HTTP error during upload: {e}")
                except Exception as e:
                    raise UploadError(f"Upload error: {e}")
            
            if response:
                video_id = response.get('id')
                self.logger.info(f"Video uploaded successfully! ID: {video_id}")
                
                # Upload thumbnail if provided
                if thumbnail_path and thumbnail_path.exists():
                    self._upload_thumbnail(video_id, thumbnail_path)
                
                # Update project with video ID
                project.youtube_video_id = video_id
                project.update_status(ProjectStatus.UPLOADED)
                
                return {
                    'success': True,
                    'video_id': video_id,
                    'video_url': f'https://youtube.com/shorts/{video_id}',
                    'response': response
                }
            else:
                raise UploadError("No response from YouTube API")
                
        except Exception as e:
            dev_error_logger.log_error(
                module="SocialMediaManager",
                error_type="YouTubeUploadError",
                description=f"Failed to upload video to YouTube",
                exception=e
            )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_shorts_video(self, video_path: Path) -> bool:
        """Validate that video meets YouTube Shorts requirements."""
        try:
            # Check file size (less than 100MB for Shorts)
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 100:
                self.logger.warning(f"Video file too large: {file_size_mb:.1f}MB")
                return False
            
            # Check video properties using ffprobe if available
            try:
                import subprocess
                import json
                
                cmd = [
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    '-show_streams',
                    str(video_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    info = json.loads(result.stdout)
                    
                    # Check duration
                    duration = float(info['format'].get('duration', 0))
                    if duration > self.SHORTS_MAX_DURATION:
                        self.logger.warning(f"Video too long: {duration}s")
                        return False
                    
                    # Check aspect ratio
                    video_stream = next((s for s in info['streams'] 
                                       if s['codec_type'] == 'video'), None)
                    if video_stream:
                        width = int(video_stream.get('width', 0))
                        height = int(video_stream.get('height', 0))
                        if height > 0:
                            aspect_ratio = width / height
                            if abs(aspect_ratio - self.SHORTS_ASPECT_RATIO) > 0.1:
                                self.logger.warning(f"Invalid aspect ratio: {aspect_ratio}")
                                # Don't fail on aspect ratio as YouTube can handle it
                
            except Exception as e:
                self.logger.warning(f"Could not validate with ffprobe: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Video validation failed: {e}")
            return False
    
    def _prepare_youtube_metadata(
        self,
        project: Project,
        schedule_time: Optional[datetime]
    ) -> Dict[str, Any]:
        """Prepare metadata for YouTube upload."""
        # Get base metadata from project
        metadata = project.video_metadata
        
        # Ensure title includes #Shorts
        title = metadata.title or project.script.title if project.script else "YouTube Short"
        if "#Shorts" not in title and "#shorts" not in title:
            title = f"{title} #Shorts"
        
        # Truncate if too long
        if len(title) > self.upload_settings['title_limit']:
            title = title[:self.upload_settings['title_limit'] - 10] + "... #Shorts"
        
        # Prepare description
        description = metadata.description or ""
        if project.script:
            description = f"{project.script.description}\n\n{description}"
        
        # Add affiliate disclaimer
        disclaimer = self._get_affiliate_disclaimer()
        description = f"{description}\n\n{disclaimer}"
        
        # Add affiliate link if configured to do so
        if self.config.get("youtube.include_affiliate_link", True) and project.affiliate_url:
            description = f"{description}\n\n🔗 {project.affiliate_url}"
        
        # Truncate description if too long
        if len(description) > self.upload_settings['description_limit']:
            description = description[:self.upload_settings['description_limit'] - 3] + "..."
        
        # Prepare tags
        tags = list(metadata.tags) if metadata.tags else []
        if project.script and project.script.tags:
            tags.extend(project.script.tags)
        
        # Add default tags
        default_tags = ["Shorts", "YouTubeShorts", "アフィリエイト", "商品紹介"]
        tags.extend(default_tags)
        
        # Remove duplicates and limit total character count
        tags = list(dict.fromkeys(tags))  # Remove duplicates while preserving order
        
        # Ensure tags don't exceed character limit
        final_tags = []
        char_count = 0
        for tag in tags:
            if char_count + len(tag) + 1 < self.upload_settings['tags_limit']:
                final_tags.append(tag)
                char_count += len(tag) + 1
            else:
                break
        
        return {
            'title': title,
            'description': description,
            'tags': final_tags,
            'category_id': metadata.category_id or self.upload_settings['category_id'],
            'privacy_status': metadata.privacy_status or self.upload_settings['privacy_status'],
            'made_for_kids': metadata.made_for_kids or self.upload_settings['made_for_kids'],
            'default_language': metadata.default_language or self.upload_settings['default_language'],
            'notify_subscribers': self.upload_settings['notify_subscribers']
        }
    
    def _get_affiliate_disclaimer(self) -> str:
        """Get affiliate disclaimer text."""
        disclaimer = self.config.get("youtube.affiliate_disclaimer")
        if disclaimer:
            return disclaimer
        
        # Default disclaimer in Japanese
        return (
            "※このビデオにはアフィリエイトリンクが含まれています。"
            "リンクから商品を購入すると、私に少額の手数料が入ります。"
            "これはあなたの購入価格には影響しません。"
        )
    
    def _upload_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """Upload thumbnail for a video."""
        try:
            media = MediaFileUpload(
                str(thumbnail_path),
                mimetype='image/png',
                resumable=True
            )
            
            request = self.youtube_service.thumbnails().set(
                videoId=video_id,
                media_body=media
            )
            
            response = request.execute()
            self.logger.info(f"Thumbnail uploaded for video {video_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload thumbnail: {e}")
            return False
    
    @handle_errors("SocialMediaManager")
    def schedule_uploads(
        self,
        projects: List[Project],
        start_time: datetime,
        interval_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Schedule multiple videos for upload.
        
        Args:
            projects: List of projects to upload
            start_time: First upload time
            interval_hours: Hours between uploads
            
        Returns:
            List of upload results
        """
        results = []
        current_time = start_time
        
        for project in projects:
            # Find video file
            if not project.final_video_path or not project.final_video_path.exists():
                self.logger.warning(f"No video found for project {project.id}")
                results.append({
                    'project_id': project.id,
                    'success': False,
                    'error': 'Video file not found'
                })
                continue
            
            # Schedule upload
            result = self.upload_to_youtube(
                video_path=project.final_video_path,
                project=project,
                thumbnail_path=project.video_metadata.thumbnail_path,
                schedule_time=current_time
            )
            
            results.append({
                'project_id': project.id,
                'scheduled_time': current_time.isoformat(),
                **result
            })
            
            # Increment time for next video
            current_time += timedelta(hours=interval_hours)
            
            # Add some delay to avoid rate limiting
            time.sleep(2)
        
        return results
    
    @handle_errors("SocialMediaManager")
    def get_video_analytics(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get analytics for an uploaded video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with video statistics or None
        """
        if not self.youtube_service:
            return None
        
        try:
            request = self.youtube_service.videos().list(
                part="statistics,snippet,status",
                id=video_id
            )
            
            response = request.execute()
            
            if response.get('items'):
                video = response['items'][0]
                
                return {
                    'video_id': video_id,
                    'title': video['snippet'].get('title'),
                    'published_at': video['snippet'].get('publishedAt'),
                    'privacy_status': video['status'].get('privacyStatus'),
                    'statistics': {
                        'views': int(video['statistics'].get('viewCount', 0)),
                        'likes': int(video['statistics'].get('likeCount', 0)),
                        'comments': int(video['statistics'].get('commentCount', 0)),
                        'favorites': int(video['statistics'].get('favoriteCount', 0))
                    }
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get video analytics: {e}")
            return None
    
    @handle_errors("SocialMediaManager")
    def update_video_metadata(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category_id: Optional[str] = None
    ) -> bool:
        """Update metadata for an existing video.
        
        Args:
            video_id: YouTube video ID
            title: New title
            description: New description
            tags: New tags
            category_id: New category
            
        Returns:
            True if successful
        """
        if not self.youtube_service:
            return False
        
        try:
            # First get the current video data
            request = self.youtube_service.videos().list(
                part="snippet",
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                self.logger.error(f"Video not found: {video_id}")
                return False
            
            # Update the snippet
            snippet = response['items'][0]['snippet']
            
            if title:
                snippet['title'] = title
            if description:
                snippet['description'] = description
            if tags:
                snippet['tags'] = tags
            if category_id:
                snippet['categoryId'] = category_id
            
            # Update the video
            update_request = self.youtube_service.videos().update(
                part="snippet",
                body={
                    'id': video_id,
                    'snippet': snippet
                }
            )
            
            update_response = update_request.execute()
            self.logger.info(f"Updated video metadata for {video_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update video metadata: {e}")
            return False
    
    def check_api_quota(self) -> Optional[Dict[str, Any]]:
        """Check YouTube API quota usage.
        
        Returns:
            Dictionary with quota information or None
        """
        # YouTube API doesn't provide direct quota checking
        # This is a placeholder for quota management
        return {
            'daily_limit': 10000,  # Default YouTube API quota
            'warning': 'Actual quota usage not available through API'
        }