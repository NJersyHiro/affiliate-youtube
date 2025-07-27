#!/usr/bin/env python3
"""Simple usage example of YouTube Shorts Generator."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.main import YouTubeShortsGenerator


def main():
    """Run a simple example."""
    # Initialize generator
    generator = YouTubeShortsGenerator()
    
    # Create a video
    result = generator.create_and_post(
        service_name="タニタ公式ネット通販サイト「タニタオンラインショップ」",
        affiliate_url="https://example.com/affiliate/tanita",
        style="humorous",
        auto_post=False  # Don't auto-post for demo
    )
    
    if result['success']:
        print("✅ Video created successfully!")
        print(f"Video path: {result['video_path']}")
        print(f"Project saved to: {result['project_file']}")
    else:
        print(f"❌ Failed: {result['error']}")


if __name__ == "__main__":
    main()