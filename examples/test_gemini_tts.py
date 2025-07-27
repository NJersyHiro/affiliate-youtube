#!/usr/bin/env python3
"""Test script for Gemini TTS functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.modules.voice_synthesizer import VoiceSynthesizer
from src.models.script import ScriptSegment
from src.models.audio import AudioSettings
from src.utils import Config


def test_gemini_tts():
    """Test Gemini TTS with different emotions and voices."""
    
    # Initialize config
    config = Config()
    
    # Create voice synthesizer with Gemini
    synthesizer = VoiceSynthesizer(config)
    
    print("🎤 Testing Gemini TTS...")
    print(f"Provider: {synthesizer.provider}")
    print(f"Available voices: {len(synthesizer.gemini_voices)}")
    
    # Test segments with different emotions
    test_segments = [
        {
            "text": "こんにちは！今日は素晴らしい商品を紹介します！",
            "emotion": "excited",
            "id": "test_1"
        },
        {
            "text": "この商品の特徴を詳しく説明しますね。",
            "emotion": "neutral",
            "id": "test_2"
        },
        {
            "text": "なんと、今なら特別価格でご提供！",
            "emotion": "surprised",
            "id": "test_3"
        },
        {
            "text": "気になった方は、説明欄のリンクをチェックしてください。",
            "emotion": "happy",
            "id": "test_4"
        }
    ]
    
    print("\n📝 Testing different emotions:")
    
    for segment_data in test_segments:
        # Create script segment
        segment = ScriptSegment(
            id=segment_data["id"],
            text=segment_data["text"],
            duration=3.0,
            emotion=segment_data["emotion"],
            emphasis_words=[]
        )
        
        print(f"\n- Emotion: {segment.emotion}")
        print(f"  Text: {segment.text}")
        
        try:
            # Synthesize audio
            audio_clip = synthesizer.synthesize_segment(segment)
            print(f"  ✅ Success! Audio saved to: {audio_clip.file_path}")
            print(f"  Duration: {audio_clip.duration:.2f}s")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    # Show available voices
    print("\n🎯 Available Gemini voices:")
    voices = synthesizer.get_available_voices()
    for lang, voice_list in voices.items():
        print(f"\n{lang}:")
        for i, voice in enumerate(voice_list[:10]):  # Show first 10
            print(f"  - {voice['name']}")
        if len(voice_list) > 10:
            print(f"  ... and {len(voice_list) - 10} more")


if __name__ == "__main__":
    test_gemini_tts()