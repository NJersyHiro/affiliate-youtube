"""Voice synthesis module for converting text to speech."""

import os
import io
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import tempfile

from ..models.audio import AudioClip, AudioSettings
from ..models.script import ScriptSegment
from ..utils import Config, get_logger, handle_errors, dev_error_logger
from ..utils.exceptions import TTSError, ConfigurationError


class VoiceSynthesizer:
    """Synthesize voice from text using various TTS providers."""
    
    SUPPORTED_PROVIDERS = ["mock", "gemini", "google_cloud", "azure", "aws", "elevenlabs"]
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the voice synthesizer.
        
        Args:
            config: Configuration object. If not provided, will create default.
        """
        self.config = config or Config()
        self.logger = get_logger(__name__)
        
        # Get TTS provider from config
        self.provider = self.config.get("tts.provider", "gemini")
        if self.provider not in self.SUPPORTED_PROVIDERS:
            raise ConfigurationError(f"Unsupported TTS provider: {self.provider}")
        
        # Initialize the appropriate TTS client
        self._init_tts_client()
        
        # Ensure output directory exists
        self.output_dir = self.config.get_output_path(
            self.config.get("output.audio_dir", "audio")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _init_tts_client(self) -> None:
        """Initialize the TTS client based on provider."""
        try:
            if self.provider == "mock":
                self._init_mock_tts()
            elif self.provider == "gemini":
                self._init_gemini_tts()
            elif self.provider == "google_cloud":
                self._init_google_cloud_tts()
            elif self.provider == "azure":
                self._init_azure_tts()
            elif self.provider == "aws":
                self._init_aws_tts()
            elif self.provider == "elevenlabs":
                self._init_elevenlabs_tts()
                
            self.logger.info(f"Initialized {self.provider} TTS client")
            
        except Exception as e:
            dev_error_logger.log_error(
                module="VoiceSynthesizer",
                error_type="TTSInitError",
                description=f"Failed to initialize {self.provider} TTS client",
                exception=e
            )
            raise TTSError(f"TTS initialization failed: {str(e)}")
    
    def _init_mock_tts(self) -> None:
        """Initialize mock TTS for testing."""
        self.logger.info("Initialized mock TTS provider for testing")
        # No actual initialization needed for mock
    
    def _init_gemini_tts(self) -> None:
        """Initialize Gemini TTS client."""
        try:
            # Check which library is available
            try:
                from google import genai
                self.use_new_genai = True
                self.logger.info("Using new google.genai library for TTS")
            except ImportError:
                import google.generativeai as genai
                self.use_new_genai = False
                self.logger.info("Using google.generativeai library (TTS may be limited)")
            
            # Get API key from config or environment
            api_key = self.config.get("ai.gemini.api_key") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ConfigurationError("Google API key not found for Gemini TTS")
            
            # Store API key for later use
            self.gemini_api_key = api_key
            
            # Store the model name for TTS
            self.gemini_model_name = "gemini-2.5-flash-preview-tts"  # Correct model for TTS
            
            # Cache available voices
            self._cache_gemini_voices()
            
            self.logger.info("Initialized Gemini TTS client")
            
        except ImportError:
            raise TTSError("Neither google.genai nor google-generativeai is installed. "
                         "Install with: pip install google-generativeai")
        except Exception as e:
            raise TTSError(f"Gemini TTS initialization failed: {str(e)}")
    
    def _cache_gemini_voices(self) -> None:
        """Cache available Gemini voices."""
        # Updated list based on the error message
        self.gemini_voices = [
            "achernar", "achird", "algenib", "algieba", "alnilam", "aoede", 
            "autonoe", "callirrhoe", "charon", "despina", "enceladus", "erinome", 
            "fenrir", "gacrux", "iapetus", "kore", "laomedeia", "leda", "orus", 
            "puck", "pulcherrima", "rasalgethi", "sadachbia", "sadaltager", 
            "schedar", "sulafat", "umbriel", "vindemiatrix", "zephyr", "zubenelgenubi"
        ]
        
        # Map emotions to suitable voices for Japanese content
        self.emotion_voice_map = {
            "excited": ["puck", "fenrir", "orus"],
            "happy": ["kore", "aoede", "callirrhoe"],
            "surprised": ["zephyr", "enceladus", "umbriel"],
            "curious": ["autonoe", "iapetus", "vindemiatrix"],
            "neutral": ["aoede", "algenib", "schedar"]
        }
        
        self.logger.info(f"Cached {len(self.gemini_voices)} Gemini voices")
    
    def _init_google_cloud_tts(self) -> None:
        """Initialize Google Cloud TTS client."""
        try:
            from google.cloud import texttospeech
            
            # Get credentials
            credentials_path = self.config.get("tts.google_cloud.credentials_path")
            if credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            
            self.tts_client = texttospeech.TextToSpeechClient()
            
            # Cache available voices
            self._cache_google_voices()
            
        except ImportError:
            raise TTSError("google-cloud-texttospeech not installed. "
                         "Install with: pip install google-cloud-texttospeech")
        except Exception as e:
            raise TTSError(f"Google Cloud TTS initialization failed: {str(e)}")
    
    def _cache_google_voices(self) -> None:
        """Cache available Google Cloud voices."""
        try:
            from google.cloud import texttospeech
            
            response = self.tts_client.list_voices()
            self.available_voices = {}
            
            for voice in response.voices:
                lang_code = voice.language_codes[0]
                if lang_code not in self.available_voices:
                    self.available_voices[lang_code] = []
                    
                self.available_voices[lang_code].append({
                    "name": voice.name,
                    "ssml_gender": voice.ssml_gender.name,
                    "natural_sample_rate_hertz": voice.natural_sample_rate_hertz
                })
                
            self.logger.info(f"Cached {len(response.voices)} Google Cloud voices")
            
        except Exception as e:
            self.logger.warning(f"Failed to cache Google voices: {e}")
            self.available_voices = {}
    
    def _init_azure_tts(self) -> None:
        """Initialize Azure TTS client."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # Get credentials
            api_key = self.config.get("tts.azure.api_key") or os.getenv("AZURE_SPEECH_KEY")
            region = self.config.get("tts.azure.region", "japaneast")
            
            if not api_key:
                raise ConfigurationError("Azure Speech API key not found")
            
            # Create speech config
            self.speech_config = speechsdk.SpeechConfig(
                subscription=api_key,
                region=region
            )
            
            # Set default voice
            voice_name = self.config.get("tts.azure.voice_name", "ja-JP-NanamiNeural")
            self.speech_config.speech_synthesis_voice_name = voice_name
            
        except ImportError:
            raise TTSError("azure-cognitiveservices-speech not installed. "
                         "Install with: pip install azure-cognitiveservices-speech")
        except Exception as e:
            raise TTSError(f"Azure TTS initialization failed: {str(e)}")
    
    def _init_aws_tts(self) -> None:
        """Initialize AWS Polly client."""
        try:
            import boto3
            
            # Get credentials
            access_key = os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            region = self.config.get("tts.aws.region", "us-east-1")
            
            if access_key and secret_key:
                self.polly_client = boto3.client(
                    'polly',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
            else:
                # Use default credentials
                self.polly_client = boto3.client('polly', region_name=region)
                
        except ImportError:
            raise TTSError("boto3 not installed. Install with: pip install boto3")
        except Exception as e:
            raise TTSError(f"AWS Polly initialization failed: {str(e)}")
    
    def _init_elevenlabs_tts(self) -> None:
        """Initialize ElevenLabs TTS client."""
        try:
            from elevenlabs import set_api_key, generate
            
            api_key = self.config.get("tts.elevenlabs.api_key") or os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                raise ConfigurationError("ElevenLabs API key not found")
                
            set_api_key(api_key)
            self.elevenlabs_generate = generate
            
        except ImportError:
            raise TTSError("elevenlabs not installed. Install with: pip install elevenlabs")
        except Exception as e:
            raise TTSError(f"ElevenLabs initialization failed: {str(e)}")
    
    @handle_errors("VoiceSynthesizer")
    def synthesize_segment(
        self,
        segment: ScriptSegment,
        settings: Optional[AudioSettings] = None,
        output_path: Optional[Path] = None
    ) -> AudioClip:
        """Synthesize audio for a single script segment.
        
        Args:
            segment: The script segment to synthesize
            settings: Audio settings override. If not provided, uses defaults
            output_path: Custom output path. If not provided, generates one
            
        Returns:
            AudioClip object with the synthesized audio
        """
        if not settings:
            settings = self._get_default_settings()
            
        # Prepare text for TTS
        text = self._prepare_text(segment.text)
        
        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"segment_{segment.id}_{timestamp}.mp3"
            output_path = self.output_dir / filename
            
        # Synthesize based on provider
        audio_data = None
        if self.provider == "mock":
            audio_data = self._synthesize_mock(text, settings, segment.emotion)
        elif self.provider == "gemini":
            audio_data = self._synthesize_gemini(text, settings, segment.emotion)
        elif self.provider == "google_cloud":
            audio_data = self._synthesize_google_cloud(text, settings, segment.emotion)
        elif self.provider == "azure":
            audio_data = self._synthesize_azure(text, settings, segment.emotion)
        elif self.provider == "aws":
            audio_data = self._synthesize_aws(text, settings, segment.emotion)
        elif self.provider == "elevenlabs":
            audio_data = self._synthesize_elevenlabs(text, settings, segment.emotion)
            
        if not audio_data:
            raise TTSError("Failed to synthesize audio")
            
        # Save audio file
        self._save_audio(audio_data, output_path)
        
        # Get audio duration
        duration = self._get_audio_duration(output_path)
        
        # Create AudioClip object
        audio_clip = AudioClip(
            segment_id=segment.id,
            text=segment.text,
            file_path=output_path,
            duration=duration,
            settings=settings
        )
        
        self.logger.info(f"Synthesized audio for segment {segment.id}: "
                        f"{duration:.1f}s, saved to {output_path}")
        
        return audio_clip
    
    def _get_default_settings(self) -> AudioSettings:
        """Get default audio settings from config."""
        provider_config = self.config.get(f"tts.{self.provider}", {})
        
        return AudioSettings(
            provider=self.provider,
            language_code=provider_config.get("language_code", "ja-JP"),
            voice_name=provider_config.get("voice_name", self._get_default_voice()),
            speaking_rate=provider_config.get("speaking_rate", 1.0),
            pitch=provider_config.get("pitch", 0.0),
            volume_gain_db=provider_config.get("volume_gain_db", 0.0),
            audio_encoding=provider_config.get("audio_encoding", "MP3"),
            sample_rate_hz=provider_config.get("sample_rate_hz", 24000)
        )
    
    def _get_default_voice(self) -> str:
        """Get default voice for the provider."""
        defaults = {
            "mock": "test-voice",
            "gemini": "kore",  # Lowercase based on error message
            "google_cloud": "ja-JP-Neural2-B",
            "azure": "ja-JP-NanamiNeural",
            "aws": "Mizuki",
            "elevenlabs": "Bella"
        }
        return defaults.get(self.provider, "")
    
    def _prepare_text(self, text: str) -> str:
        """Prepare text for TTS processing."""
        # Remove pause markers and clean up
        text = text.replace('<pause>', ' ')
        text = text.replace('<pause:0.2>', ' ')
        text = text.replace('<pause:0.3>', ' ')
        
        # Clean up extra spaces
        import re
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _synthesize_mock(
        self,
        text: str,
        settings: AudioSettings,
        emotion: str
    ) -> bytes:
        """Mock TTS synthesis for testing."""
        try:
            # Create a simple mock audio data (silent WAV file)
            import wave
            import struct
            
            # Create a simple sine wave for testing
            duration = len(text) / 5.0  # Estimate duration based on text length
            sample_rate = 44100
            num_samples = int(duration * sample_rate)
            
            # Generate silent audio (zeros)
            audio_data = b''.join(
                struct.pack('<h', 0) for _ in range(num_samples)
            )
            
            # Create WAV header
            num_channels = 1
            bits_per_sample = 16
            byte_rate = sample_rate * num_channels * bits_per_sample // 8
            block_align = num_channels * bits_per_sample // 8
            
            wav_header = struct.pack(
                '<4sI4s4sIHHIIHH4sI',
                b'RIFF',
                36 + len(audio_data),
                b'WAVE',
                b'fmt ',
                16,  # Subchunk1Size
                1,   # AudioFormat (PCM)
                num_channels,
                sample_rate,
                byte_rate,
                block_align,
                bits_per_sample,
                b'data',
                len(audio_data)
            )
            
            self.logger.info(f"Mock TTS: Generated {duration:.1f}s of audio for {len(text)} chars")
            return wav_header + audio_data
            
        except Exception as e:
            raise TTSError(f"Mock TTS synthesis failed: {str(e)}")
    
    def _synthesize_gemini(
        self,
        text: str,
        settings: AudioSettings,
        emotion: str
    ) -> bytes:
        """Synthesize using Gemini TTS."""
        try:
            # Use the new google.genai client library
            from google import genai
            from google.genai import types
            
            # Select voice based on emotion
            voice_name = settings.voice_name
            if emotion in self.emotion_voice_map and voice_name == self._get_default_voice():
                # Use emotion-appropriate voice if using default
                voice_name = self.emotion_voice_map[emotion][0]
            
            # Create natural language prompt for emotion control
            emotion_prompts = {
                "excited": "Say this with excitement and enthusiasm: ",
                "happy": "Say this cheerfully and warmly: ",
                "surprised": "Say this with surprise and amazement: ",
                "curious": "Say this with curiosity and interest: ",
                "neutral": ""
            }
            
            prompt_prefix = emotion_prompts.get(emotion, "")
            full_text = prompt_prefix + text
            
            # Get API key
            api_key = self.config.get("ai.gemini.api_key") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ConfigurationError("Google API key not found for Gemini TTS")
            
            # Remove Vertex AI environment variables to ensure we use Gemini Developer API
            vertex_ai_vars = ['GOOGLE_GENAI_USE_VERTEXAI', 'GOOGLE_CLOUD_PROJECT', 'GOOGLE_CLOUD_LOCATION']
            for var in vertex_ai_vars:
                if var in os.environ:
                    del os.environ[var]
                    self.logger.info(f"Removed {var} environment variable to use Gemini Developer API")
            
            # Create the client with explicit API key
            client = genai.Client(api_key=api_key)
            
            # Generate audio with speech config
            response = client.models.generate_content(
                model=self.gemini_model_name,
                contents=full_text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        )
                    ),
                )
            )
            
            # Extract audio data from response (following the official example)
            inline_data = response.candidates[0].content.parts[0].inline_data
            
            # Handle base64 encoding if necessary
            if isinstance(inline_data.data, str):
                # Base64 encoded data
                import base64
                audio_data = base64.b64decode(inline_data.data)
                self.logger.info(f"Decoded base64 audio data: {len(audio_data)} bytes")
            else:
                # Binary data
                audio_data = inline_data.data
                self.logger.info(f"Raw audio data: {len(audio_data)} bytes")
            
            # Return raw PCM data - it will be saved as WAV by _save_audio
            return audio_data
            
        except ImportError as e:
            # Try falling back to google.generativeai if google.genai is not available
            self.logger.warning("google.genai not available, trying google.generativeai")
            return self._synthesize_gemini_legacy(text, settings, emotion)
        except Exception as e:
            dev_error_logger.log_error(
                module="VoiceSynthesizer",
                error_type="GeminiTTSError",
                description=f"Failed to synthesize with Gemini TTS",
                exception=e
            )
            raise TTSError(f"Gemini TTS synthesis failed: {str(e)}")
    
    def _synthesize_gemini_legacy(
        self,
        text: str,
        settings: AudioSettings,
        emotion: str
    ) -> bytes:
        """Legacy Gemini TTS synthesis using google.generativeai."""
        try:
            import google.generativeai as genai
            
            # Check if we should try Google Cloud TTS as fallback
            if self.config.get("tts.gemini.fallback_to_google_cloud", False):
                self.logger.warning("Gemini TTS not available, falling back to Google Cloud TTS")
                # Temporarily switch provider
                original_provider = self.provider
                self.provider = "google_cloud"
                try:
                    # Initialize Google Cloud TTS if not already done
                    if not hasattr(self, 'tts_client'):
                        self._init_google_cloud_tts()
                    result = self._synthesize_google_cloud(text, settings, emotion)
                    self.provider = original_provider
                    return result
                except Exception as e:
                    self.provider = original_provider
                    self.logger.error(f"Google Cloud TTS fallback failed: {e}")
            
            # Fall back to mock TTS
            self.logger.warning(
                "Gemini TTS is not available in the current SDK version. "
                "Audio generation requires the new google.genai SDK with proper authentication. "
                "Using mock TTS for testing. To use real TTS, please configure Google Cloud TTS."
            )
            return self._synthesize_mock(text, settings, emotion)
            
        except Exception as e:
            raise TTSError(f"Legacy Gemini TTS failed: {str(e)}")
    
    def _synthesize_google_cloud(
        self,
        text: str,
        settings: AudioSettings,
        emotion: str
    ) -> bytes:
        """Synthesize using Google Cloud TTS."""
        try:
            from google.cloud import texttospeech
            
            # Create synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Create voice selection
            voice = texttospeech.VoiceSelectionParams(
                language_code=settings.language_code,
                name=settings.voice_name
            )
            
            # Create audio config with emotion adjustments
            audio_config = texttospeech.AudioConfig(
                audio_encoding=getattr(
                    texttospeech.AudioEncoding,
                    settings.audio_encoding
                ),
                speaking_rate=self._adjust_rate_for_emotion(settings.speaking_rate, emotion),
                pitch=self._adjust_pitch_for_emotion(settings.pitch, emotion),
                volume_gain_db=settings.volume_gain_db
            )
            
            # Perform synthesis
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            return response.audio_content
            
        except Exception as e:
            dev_error_logger.log_error(
                module="VoiceSynthesizer",
                error_type="GoogleCloudTTSError",
                description=f"Failed to synthesize with Google Cloud TTS",
                exception=e
            )
            raise TTSError(f"Google Cloud TTS synthesis failed: {str(e)}")
    
    def _synthesize_azure(
        self,
        text: str,
        settings: AudioSettings,
        emotion: str
    ) -> bytes:
        """Synthesize using Azure TTS."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # Create SSML with emotion
            ssml = self._create_azure_ssml(text, settings, emotion)
            
            # Create synthesizer
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=False)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Synthesize
            result = synthesizer.speak_ssml_async(ssml).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return result.audio_data
            else:
                raise TTSError(f"Azure synthesis failed: {result.reason}")
                
        except Exception as e:
            dev_error_logger.log_error(
                module="VoiceSynthesizer",
                error_type="AzureTTSError",
                description=f"Failed to synthesize with Azure TTS",
                exception=e
            )
            raise TTSError(f"Azure TTS synthesis failed: {str(e)}")
    
    def _create_azure_ssml(self, text: str, settings: AudioSettings, emotion: str) -> str:
        """Create SSML for Azure TTS with emotion."""
        emotion_styles = {
            "excited": "cheerful",
            "happy": "friendly",
            "surprised": "excited",
            "curious": "customerservice",
            "neutral": "neutral"
        }
        
        style = emotion_styles.get(emotion, "neutral")
        
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" 
               xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{settings.language_code}">
            <voice name="{settings.voice_name}">
                <mstts:express-as style="{style}" styledegree="1.5">
                    <prosody rate="{settings.speaking_rate}" pitch="{settings.pitch}Hz">
                        {text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
        
        return ssml
    
    def _synthesize_aws(
        self,
        text: str,
        settings: AudioSettings,
        emotion: str
    ) -> bytes:
        """Synthesize using AWS Polly."""
        try:
            # Create SSML
            ssml = self._create_polly_ssml(text, settings, emotion)
            
            # Synthesize
            response = self.polly_client.synthesize_speech(
                Text=ssml,
                TextType='ssml',
                OutputFormat=settings.audio_encoding.lower(),
                VoiceId=settings.voice_name,
                SampleRate=str(settings.sample_rate_hz)
            )
            
            # Read audio stream
            audio_stream = response.get('AudioStream')
            if audio_stream:
                return audio_stream.read()
            else:
                raise TTSError("No audio stream in Polly response")
                
        except Exception as e:
            dev_error_logger.log_error(
                module="VoiceSynthesizer",
                error_type="AWSPollyError",
                description=f"Failed to synthesize with AWS Polly",
                exception=e
            )
            raise TTSError(f"AWS Polly synthesis failed: {str(e)}")
    
    def _create_polly_ssml(self, text: str, settings: AudioSettings, emotion: str) -> str:
        """Create SSML for AWS Polly."""
        # Adjust rate and pitch for emotion
        rate = self._adjust_rate_for_emotion(settings.speaking_rate, emotion)
        rate_percent = int(rate * 100)
        
        ssml = f"""
        <speak>
            <prosody rate="{rate_percent}%" pitch="{settings.pitch}%">
                {text}
            </prosody>
        </speak>
        """
        
        return ssml
    
    def _synthesize_elevenlabs(
        self,
        text: str,
        settings: AudioSettings,
        emotion: str
    ) -> bytes:
        """Synthesize using ElevenLabs."""
        try:
            # Adjust voice settings for emotion
            voice_settings = {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
            
            if emotion == "excited":
                voice_settings["stability"] = 0.3
                voice_settings["similarity_boost"] = 0.9
            elif emotion == "happy":
                voice_settings["stability"] = 0.4
                voice_settings["similarity_boost"] = 0.8
                
            # Generate audio
            audio = self.elevenlabs_generate(
                text=text,
                voice=settings.voice_name,
                model="eleven_multilingual_v2",
                voice_settings=voice_settings
            )
            
            # Convert generator to bytes
            audio_bytes = b''.join(audio)
            return audio_bytes
            
        except Exception as e:
            dev_error_logger.log_error(
                module="VoiceSynthesizer",
                error_type="ElevenLabsError",
                description=f"Failed to synthesize with ElevenLabs",
                exception=e
            )
            raise TTSError(f"ElevenLabs synthesis failed: {str(e)}")
    
    def _adjust_rate_for_emotion(self, base_rate: float, emotion: str) -> float:
        """Adjust speaking rate based on emotion."""
        adjustments = {
            "excited": 1.1,
            "happy": 1.05,
            "surprised": 1.15,
            "curious": 0.95,
            "neutral": 1.0
        }
        return base_rate * adjustments.get(emotion, 1.0)
    
    def _adjust_pitch_for_emotion(self, base_pitch: float, emotion: str) -> float:
        """Adjust pitch based on emotion."""
        adjustments = {
            "excited": 2.0,
            "happy": 1.0,
            "surprised": 3.0,
            "curious": 1.0,
            "neutral": 0.0
        }
        return base_pitch + adjustments.get(emotion, 0.0)
    
    def _save_audio(self, audio_data: bytes, output_path: Path) -> None:
        """Save audio data to file."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if this is raw PCM data from Gemini TTS
            if self.provider == "gemini" and output_path.suffix.lower() in ['.wav', '.mp3']:
                # Save as WAV file with proper header
                import wave
                import struct
                
                # Gemini TTS returns PCM data at 24kHz, 16-bit, mono
                sample_rate = 24000
                channels = 1
                sample_width = 2  # 16-bit
                
                with wave.open(str(output_path), 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(sample_width)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_data)
                    
                self.logger.info(f"Saved Gemini TTS audio as WAV: {output_path}")
            else:
                # For other providers or formats, save as-is
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                    
        except Exception as e:
            raise TTSError(f"Failed to save audio file: {str(e)}")
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0  # Convert milliseconds to seconds
            
        except ImportError:
            self.logger.warning("pydub not available, returning estimated duration")
            # Estimate based on file size (rough approximation)
            file_size = audio_path.stat().st_size
            # Assume 128 kbps MP3
            return file_size / (128 * 1000 / 8)
        except Exception as e:
            self.logger.warning(f"Failed to get audio duration: {e}")
            return 0.0
    
    @handle_errors("VoiceSynthesizer")
    def synthesize_script(
        self,
        segments: List[Dict[str, Any]],
        project_id: str
    ) -> List[AudioClip]:
        """Synthesize audio for multiple script segments.
        
        Args:
            segments: List of segment dictionaries from ScriptProcessor
            project_id: Project ID for organizing output
            
        Returns:
            List of AudioClip objects
        """
        audio_clips = []
        project_audio_dir = self.output_dir / project_id
        project_audio_dir.mkdir(parents=True, exist_ok=True)
        
        for i, segment_data in enumerate(segments):
            try:
                # Create a temporary ScriptSegment object
                segment = ScriptSegment(
                    id=segment_data["id"],
                    text=segment_data["text"],
                    duration=segment_data["duration"],
                    emotion=segment_data.get("emotion", "neutral"),
                    emphasis_words=segment_data.get("emphasis_words", [])
                )
                
                # Generate output path
                output_path = project_audio_dir / f"segment_{i+1:02d}.mp3"
                
                # Synthesize
                audio_clip = self.synthesize_segment(segment, output_path=output_path)
                audio_clips.append(audio_clip)
                
                self.logger.info(f"Synthesized segment {i+1}/{len(segments)}")
                
            except Exception as e:
                self.logger.error(f"Failed to synthesize segment {i+1}: {e}")
                dev_error_logger.log_error(
                    module="VoiceSynthesizer",
                    error_type="SegmentSynthesisError",
                    description=f"Failed to synthesize segment {segment_data.get('id', i)}",
                    exception=e
                )
                # Continue with other segments
                
        return audio_clips
    
    def get_available_voices(self, language_code: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get available voices for the current provider.
        
        Args:
            language_code: Filter by language code (e.g., "ja-JP")
            
        Returns:
            Dictionary mapping language codes to voice information
        """
        if self.provider == "gemini" and hasattr(self, 'gemini_voices'):
            # Gemini supports multiple languages automatically
            return {
                "multilingual": [
                    {"name": voice, "gender": "Neutral", "description": f"Gemini voice {voice}"}
                    for voice in self.gemini_voices
                ]
            }
        elif self.provider == "google_cloud" and hasattr(self, 'available_voices'):
            if language_code:
                return {language_code: self.available_voices.get(language_code, [])}
            return self.available_voices
            
        # For other providers, return predefined voices
        voices = {
            "azure": {
                "ja-JP": [
                    {"name": "ja-JP-NanamiNeural", "gender": "Female"},
                    {"name": "ja-JP-KeitaNeural", "gender": "Male"},
                    {"name": "ja-JP-AoiNeural", "gender": "Female"},
                    {"name": "ja-JP-DaichiNeural", "gender": "Male"}
                ]
            },
            "aws": {
                "ja-JP": [
                    {"name": "Mizuki", "gender": "Female"},
                    {"name": "Takumi", "gender": "Male"}
                ]
            },
            "elevenlabs": {
                "multilingual": [
                    {"name": "Bella", "gender": "Female"},
                    {"name": "Antoni", "gender": "Male"},
                    {"name": "Elli", "gender": "Female"},
                    {"name": "Josh", "gender": "Male"}
                ]
            }
        }
        
        provider_voices = voices.get(self.provider, {})
        if language_code and language_code in provider_voices:
            return {language_code: provider_voices[language_code]}
            
        return provider_voices