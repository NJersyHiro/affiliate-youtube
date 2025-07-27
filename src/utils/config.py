"""Configuration management with Google GenAI/Gemini support."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .error_handler import dev_error_logger, handle_errors


class Config:
    """Configuration manager for the YouTube Shorts Generator."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to config file. Defaults to config/default.yaml
        """
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config" / "default.yaml"
        self._config: Dict[str, Any] = {}
        self._env_loaded = False
        
        # Load configuration
        self.load_config()
        
    def load_config(self) -> None:
        """Load configuration from file and environment variables."""
        try:
            # Load environment variables
            if not self._env_loaded:
                load_dotenv()
                self._env_loaded = True
            
            # Load YAML config
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f)
                
            # Override with environment variables
            self._apply_env_overrides()
            
            # Set up Google GenAI/Gemini configuration
            self._setup_gemini_config()
            
        except FileNotFoundError:
            dev_error_logger.log_error(
                module="Config",
                error_type="FileNotFoundError",
                description=f"Config file not found: {self.config_path}",
                solution="Using default configuration"
            )
            self._config = self._get_default_config()
        except Exception as e:
            dev_error_logger.log_error(
                module="Config",
                error_type="ConfigError",
                description=f"Failed to load configuration",
                exception=e
            )
            raise
            
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        # Google GenAI API Key
        if google_api_key := os.getenv("GOOGLE_API_KEY"):
            self._config.setdefault("ai", {}).setdefault("gemini", {})["api_key"] = google_api_key
            
        # YouTube API Key
        if youtube_key := os.getenv("YOUTUBE_API_KEY"):
            self._config.setdefault("youtube", {})["api_key"] = youtube_key
            
        # TTS Keys
        if google_tts_key := os.getenv("GOOGLE_CLOUD_TTS_KEY"):
            self._config.setdefault("tts", {}).setdefault("google_cloud", {})["api_key"] = google_tts_key
            
        if azure_key := os.getenv("AZURE_SPEECH_KEY"):
            self._config.setdefault("tts", {}).setdefault("azure", {})["api_key"] = azure_key
            self._config["tts"]["azure"]["region"] = os.getenv("AZURE_SPEECH_REGION", "japaneast")
            
        # Output directory
        if output_dir := os.getenv("OUTPUT_DIR"):
            self._config["output"]["base_dir"] = output_dir
            
        # Log level
        if log_level := os.getenv("LOG_LEVEL"):
            self._config["logging"]["level"] = log_level
            
    def _setup_gemini_config(self) -> None:
        """Set up Google GenAI/Gemini specific configuration."""
        try:
            import google.generativeai as genai
            
            # Get API key
            api_key = self.get("ai.gemini.api_key") or self.get("ai.google_genai.api_key")
            if not api_key:
                raise ValueError("Google API key not found in configuration or environment")
                
            # Configure the SDK
            genai.configure(api_key=api_key)
            
            # Store configured state
            self._config.setdefault("ai", {}).setdefault("gemini", {})["configured"] = True
            
        except ImportError:
            dev_error_logger.log_error(
                module="Config",
                error_type="ImportError",
                description="google-generativeai package not installed",
                solution="Install with: pip install google-generativeai"
            )
            raise
        except Exception as e:
            dev_error_logger.log_error(
                module="Config",
                error_type="GeminiConfigError",
                description="Failed to configure Google GenAI/Gemini",
                exception=e
            )
            raise
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "project": {
                "name": "YouTube Shorts Generator",
                "version": "0.1.0"
            },
            "ai": {
                "provider": "gemini",
                "gemini": {
                    "model": "gemini-2.0-pro",  # Using 2.0 as 2.5 doesn't exist yet
                    "temperature": 0.8,
                    "max_tokens": 2048,
                    "top_p": 0.95,
                    "top_k": 40
                }
            },
            "script": {
                "styles": ["humorous", "educational", "storytelling", "comparison", "review"],
                "default_style": "humorous",
                "duration": 60,
                "segments": 3
            },
            "tts": {
                "provider": "google_cloud",
                "google_cloud": {
                    "language_code": "ja-JP",
                    "voice_name": "ja-JP-Neural2-B",
                    "speaking_rate": 1.0,
                    "pitch": 0.0
                }
            },
            "video": {
                "resolution": {"width": 1080, "height": 1920},
                "fps": 30,
                "format": "mp4",
                "max_duration": 60
            },
            "output": {
                "base_dir": "output",
                "scripts_dir": "scripts",
                "audio_dir": "audio",
                "visuals_dir": "visuals",
                "videos_dir": "videos"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
        
    @handle_errors("Config")
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'ai.gemini.model')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    @handle_errors("Config")
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        # Set the value
        config[keys[-1]] = value
        
    def get_gemini_model(self) -> Optional[Any]:
        """Get configured Gemini model instance.
        
        Returns:
            Configured GenerativeModel instance or None
        """
        try:
            import google.generativeai as genai
            
            if not self.get("ai.gemini.configured"):
                self._setup_gemini_config()
                
            model_name = self.get("ai.gemini.model", "gemini-2.0-pro")
            
            # Create model with configuration
            generation_config = {
                "temperature": self.get("ai.gemini.temperature", 0.8),
                "top_p": self.get("ai.gemini.top_p", 0.95),
                "top_k": self.get("ai.gemini.top_k", 40),
                "max_output_tokens": self.get("ai.gemini.max_tokens", 2048),
            }
            
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config
            )
            
            return model
            
        except Exception as e:
            dev_error_logger.log_error(
                module="Config",
                error_type="ModelCreationError",
                description=f"Failed to create Gemini model",
                exception=e
            )
            return None
            
    def get_output_path(self, subdir: str = "") -> Path:
        """Get output directory path.
        
        Args:
            subdir: Subdirectory within output directory
            
        Returns:
            Path object for the output directory
        """
        base_dir = Path(self.get("output.base_dir", "output"))
        if subdir:
            return base_dir / subdir
        return base_dir
        
    def ensure_output_dirs(self) -> None:
        """Ensure all output directories exist."""
        dirs = [
            self.get_output_path(),
            self.get_output_path(self.get("output.scripts_dir", "scripts")),
            self.get_output_path(self.get("output.audio_dir", "audio")),
            self.get_output_path(self.get("output.visuals_dir", "visuals")),
            self.get_output_path(self.get("output.videos_dir", "videos"))
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            
    def __repr__(self) -> str:
        """String representation of config."""
        return f"<Config: {self.config_path}>"