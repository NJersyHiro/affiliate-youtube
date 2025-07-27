"""Custom exceptions for the YouTube Shorts Generator."""


class YouTubeShortsGeneratorError(Exception):
    """Base exception for the YouTube Shorts Generator."""
    pass


class ConfigurationError(YouTubeShortsGeneratorError):
    """Raised when there's a configuration error."""
    pass


class APIError(YouTubeShortsGeneratorError):
    """Base exception for API-related errors."""
    pass


class GeminiAPIError(APIError):
    """Raised when there's an error with the Gemini API."""
    pass


class YouTubeAPIError(APIError):
    """Raised when there's an error with the YouTube API."""
    pass


class TTSError(APIError):
    """Raised when there's an error with Text-to-Speech services."""
    pass


class ScriptGenerationError(YouTubeShortsGeneratorError):
    """Raised when script generation fails."""
    pass


class VideoProcessingError(YouTubeShortsGeneratorError):
    """Raised when video processing fails."""
    pass


class AudioProcessingError(YouTubeShortsGeneratorError):
    """Raised when audio processing fails."""
    pass


class UploadError(YouTubeShortsGeneratorError):
    """Raised when upload to social media fails."""
    pass


class ValidationError(YouTubeShortsGeneratorError):
    """Raised when validation fails."""
    pass


class ResourceNotFoundError(YouTubeShortsGeneratorError):
    """Raised when a required resource is not found."""
    pass


# Export all exceptions
__all__ = [
    "YouTubeShortsGeneratorError",
    "ConfigurationError",
    "APIError",
    "GeminiAPIError",
    "YouTubeAPIError",
    "TTSError",
    "ScriptGenerationError",
    "VideoProcessingError",
    "AudioProcessingError",
    "UploadError",
    "ValidationError",
    "ResourceNotFoundError"
]