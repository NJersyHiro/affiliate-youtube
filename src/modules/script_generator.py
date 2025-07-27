"""Script generation module using Google Gemini."""

from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from ..models.script import Script, ScriptSegment, ScriptStyle
from ..utils import Config, get_logger, handle_errors, dev_error_logger
from ..utils.exceptions import ScriptGenerationError, GeminiAPIError


class ScriptGenerator:
    """Generate engaging scripts for YouTube Shorts using Gemini."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the script generator.
        
        Args:
            config: Configuration object. If not provided, will create default.
        """
        self.config = config or Config()
        self.logger = get_logger(__name__)
        self.model = None
        self._initialize_model()
        
    def _initialize_model(self) -> None:
        """Initialize the Gemini model."""
        try:
            self.model = self.config.get_gemini_model()
            if not self.model:
                raise GeminiAPIError("Failed to initialize Gemini model")
            self.logger.info("Gemini model initialized successfully")
        except Exception as e:
            dev_error_logger.log_error(
                module="ScriptGenerator",
                error_type="ModelInitError",
                description="Failed to initialize Gemini model",
                exception=e
            )
            raise GeminiAPIError(f"Model initialization failed: {str(e)}")
    
    @handle_errors("ScriptGenerator")
    def generate_script(
        self,
        service_name: str,
        affiliate_url: str,
        style: ScriptStyle = ScriptStyle.HUMOROUS,
        target_duration: int = 60,
        additional_context: Optional[str] = None
    ) -> Script:
        """Generate a script for the given service.
        
        Args:
            service_name: Name of the service to promote
            affiliate_url: Affiliate URL for the service
            style: Style of the script
            target_duration: Target duration in seconds (max 60)
            additional_context: Additional context or requirements
            
        Returns:
            Generated Script object
        """
        if not self.model:
            raise ScriptGenerationError("Model not initialized")
            
        # Prepare the prompt
        prompt = self._create_prompt(
            service_name=service_name,
            style=style,
            target_duration=min(target_duration, 60),
            additional_context=additional_context
        )
        
        try:
            # Generate the script
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                raise ScriptGenerationError("Empty response from Gemini")
                
            # Parse the response
            script_data = self._parse_response(response.text)
            
            # Create Script object
            script = self._create_script_object(
                script_data=script_data,
                service_name=service_name,
                affiliate_url=affiliate_url,
                style=style
            )
            
            self.logger.info(f"Script generated successfully for {service_name}")
            return script
            
        except Exception as e:
            dev_error_logger.log_error(
                module="ScriptGenerator",
                error_type="GenerationError",
                description=f"Failed to generate script for {service_name}",
                exception=e
            )
            raise ScriptGenerationError(f"Script generation failed: {str(e)}")
    
    def _create_prompt(
        self,
        service_name: str,
        style: ScriptStyle,
        target_duration: int,
        additional_context: Optional[str] = None
    ) -> str:
        """Create a prompt for script generation."""
        style_descriptions = {
            ScriptStyle.HUMOROUS: "面白くて楽しい、視聴者が笑顔になるような",
            ScriptStyle.EDUCATIONAL: "教育的で有益な、視聴者が学べる",
            ScriptStyle.STORYTELLING: "ストーリー性のある、感情に訴える",
            ScriptStyle.COMPARISON: "比較検討型の、客観的な視点での",
            ScriptStyle.REVIEW: "レビュー形式の、実体験に基づいた",
            ScriptStyle.DRAMATIC: "ドラマチックで印象的な、感動的な",
            ScriptStyle.CASUAL: "カジュアルで親しみやすい、友達に話すような",
            ScriptStyle.PROFESSIONAL: "プロフェッショナルで信頼性の高い"
        }
        
        style_desc = style_descriptions.get(style, style_descriptions[ScriptStyle.HUMOROUS])
        
        prompt = f"""
あなたはYouTube Shortsの台本作成の専門家です。
以下のサービスについて、{style_desc}YouTube Shorts動画の台本を作成してください。

サービス名: {service_name}
目標時間: {target_duration}秒

要件:
1. 冒頭3秒で視聴者の注意を引く強力なフック
2. 中盤でサービスの魅力を具体的に紹介
3. 終盤で行動を促す明確なCTA（Call to Action）
4. 日本語で、親しみやすい口調
5. {target_duration}秒で話せる適切な文字数（日本語で1秒あたり約5-6文字）

{f"追加の要件: {additional_context}" if additional_context else ""}

以下のJSON形式で台本を生成してください:
{{
    "title": "動画のタイトル（15文字以内）",
    "description": "動画の説明文（100文字程度）",
    "segments": [
        {{
            "text": "セグメントのテキスト",
            "duration": セグメントの秒数,
            "visual_description": "このセグメントで表示する視覚要素の説明",
            "emotion": "neutral/excited/curious/happy/surprised",
            "emphasis_words": ["強調する単語のリスト"]
        }}
    ],
    "tags": ["関連タグ", "最大10個"],
    "hashtags": ["#ハッシュタグ", "最大5個"]
}}

重要: 
- 各セグメントは10-20秒程度に収める
- 全体で3-5セグメントに分割
- 合計時間が{target_duration}秒になるように調整
"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the response from Gemini."""
        try:
            # Extract JSON from the response
            # Gemini might return markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            else:
                json_str = response_text.strip()
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["title", "description", "segments"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate segments
            if not isinstance(data["segments"], list) or len(data["segments"]) == 0:
                raise ValueError("Segments must be a non-empty list")
            
            for i, segment in enumerate(data["segments"]):
                if "text" not in segment or "duration" not in segment:
                    raise ValueError(f"Segment {i} missing required fields")
                    
                # Set defaults for optional fields
                segment.setdefault("visual_description", "")
                segment.setdefault("emotion", "neutral")
                segment.setdefault("emphasis_words", [])
            
            # Set defaults for optional fields
            data.setdefault("tags", [])
            data.setdefault("hashtags", [])
            
            return data
            
        except json.JSONDecodeError as e:
            dev_error_logger.log_error(
                module="ScriptGenerator",
                error_type="ParseError",
                description="Failed to parse JSON response from Gemini",
                solution="Check Gemini response format",
                exception=e
            )
            raise ScriptGenerationError(f"Failed to parse response: {str(e)}")
        except Exception as e:
            raise ScriptGenerationError(f"Response validation failed: {str(e)}")
    
    def _create_script_object(
        self,
        script_data: Dict[str, Any],
        service_name: str,
        affiliate_url: str,
        style: ScriptStyle
    ) -> Script:
        """Create a Script object from parsed data."""
        script = Script(
            service_name=service_name,
            affiliate_url=affiliate_url,
            style=style,
            title=script_data["title"],
            description=script_data["description"],
            tags=script_data["tags"][:10],  # Limit to 10 tags
            hashtags=script_data["hashtags"][:5]  # Limit to 5 hashtags
        )
        
        # Add segments
        for segment_data in script_data["segments"]:
            segment = ScriptSegment(
                text=segment_data["text"],
                duration=float(segment_data["duration"]),
                visual_description=segment_data["visual_description"],
                emotion=segment_data["emotion"],
                emphasis_words=segment_data["emphasis_words"]
            )
            script.add_segment(segment)
        
        # Add metadata
        script.metadata.update({
            "generator_version": "1.0",
            "model": self.config.get("ai.gemini.model", "gemini-2.0-pro"),
            "generated_at": datetime.now().isoformat()
        })
        
        return script
    
    @handle_errors("ScriptGenerator")
    def regenerate_segment(
        self,
        script: Script,
        segment_id: str,
        requirements: Optional[str] = None
    ) -> ScriptSegment:
        """Regenerate a specific segment of the script.
        
        Args:
            script: The script containing the segment
            segment_id: ID of the segment to regenerate
            requirements: Specific requirements for regeneration
            
        Returns:
            New ScriptSegment object
        """
        segment = script.get_segment(segment_id)
        if not segment:
            raise ValueError(f"Segment {segment_id} not found")
        
        prompt = f"""
以下のYouTube Shortsの台本セグメントを改善してください。

現在のセグメント:
- テキスト: {segment.text}
- 長さ: {segment.duration}秒
- 感情: {segment.emotion}

改善要件:
{requirements if requirements else "より魅力的で効果的な内容に改善してください"}

以下のJSON形式で改善されたセグメントを生成してください:
{{
    "text": "改善されたテキスト",
    "duration": {segment.duration},
    "visual_description": "視覚要素の説明",
    "emotion": "neutral/excited/curious/happy/surprised",
    "emphasis_words": ["強調する単語"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            if not response or not response.text:
                raise ScriptGenerationError("Empty response from Gemini")
            
            # Parse response
            segment_data = self._parse_segment_response(response.text)
            
            # Create new segment
            new_segment = ScriptSegment(
                text=segment_data["text"],
                duration=segment_data["duration"],
                visual_description=segment_data["visual_description"],
                emotion=segment_data["emotion"],
                emphasis_words=segment_data["emphasis_words"]
            )
            
            return new_segment
            
        except Exception as e:
            dev_error_logger.log_error(
                module="ScriptGenerator",
                error_type="RegenerationError",
                description=f"Failed to regenerate segment {segment_id}",
                exception=e
            )
            raise ScriptGenerationError(f"Segment regeneration failed: {str(e)}")
    
    def _parse_segment_response(self, response_text: str) -> Dict[str, Any]:
        """Parse segment response from Gemini."""
        try:
            # Extract JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            else:
                json_str = response_text.strip()
            
            return json.loads(json_str)
            
        except Exception as e:
            raise ScriptGenerationError(f"Failed to parse segment response: {str(e)}")