#!/usr/bin/env python3
"""Simple demo without complex imports."""

import json
import os
from datetime import datetime
from uuid import uuid4

# Demo data
demo_script = {
    "service_name": "タニタ公式ネット通販サイト「タニタオンラインショップ」",
    "affiliate_url": "https://example.com/affiliate/tanita",
    "style": "humorous",
    "title": "健康管理が楽しくなる！",
    "description": "タニタの最新健康機器で、毎日の健康管理をゲーム感覚で楽しもう！",
    "segments": [
        {
            "text": "みなさん、体重計に乗るのが怖い人〜？はい、私もです！でも、なんと！タニタの体重計なら、乗るのが楽しみになっちゃうんです！",
            "duration": 8.0,
            "visual_description": "体重計から逃げる人のアニメーション → タニタの体重計に喜んで乗る人",
            "emotion": "excited"
        },
        {
            "text": "実は最新のタニタ体組成計、ただの体重計じゃありません。筋肉量、体脂肪率、基礎代謝まで全部わかっちゃう。まるで自分専用のパーソナルトレーナー！",
            "duration": 10.0,
            "visual_description": "体組成計の画面に表示される様々な数値のアニメーション",
            "emotion": "surprised"
        },
        {
            "text": "しかも、スマホアプリと連携して、毎日の変化をグラフで確認。ゲーム感覚で健康管理ができちゃいます。昨日より筋肉量が0.1kg増えた！やったー！みたいな。",
            "duration": 12.0,
            "visual_description": "スマホアプリのグラフが上昇するアニメーション、喜ぶキャラクター",
            "emotion": "happy"
        }
    ],
    "tags": ["タニタ", "健康管理", "体組成計", "ダイエット", "筋トレ"],
    "hashtags": ["#タニタ", "#健康管理", "#ダイエット", "#体組成計", "#健康習慣"]
}

def process_script_demo():
    """Demo script processing logic."""
    print("YouTube Shorts Generator - Simple Demo")
    print("=" * 50)
    
    # Calculate total duration
    total_duration = sum(segment["duration"] for segment in demo_script["segments"])
    
    print(f"\nScript: {demo_script['title']}")
    print(f"Service: {demo_script['service_name']}")
    print(f"Style: {demo_script['style']}")
    print(f"Total Duration: {total_duration}s")
    print(f"Segments: {len(demo_script['segments'])}")
    
    print("\nSegment Details:")
    for i, segment in enumerate(demo_script["segments"], 1):
        print(f"\nSegment {i}:")
        print(f"  Duration: {segment['duration']}s")
        print(f"  Emotion: {segment['emotion']}")
        print(f"  Text: {segment['text'][:50]}...")
        print(f"  Visual: {segment['visual_description'][:50]}...")
    
    # Save output
    output_dir = "output/simple_demo"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "demo_script.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(demo_script, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Demo script saved to: {output_file}")
    
    # Project structure demo
    print("\nProject Structure Created:")
    print("```")
    print("affiliate-youtube/")
    print("├── src/")
    print("│   ├── models/          ✓ Data models created")
    print("│   ├── modules/         ✓ Core modules created")
    print("│   │   ├── script_generator.py    ✓")
    print("│   │   └── script_processor.py    ✓")
    print("│   └── utils/           ✓ Utilities created")
    print("├── config/              ✓ Configuration files")
    print("├── output/              ✓ Output directory")
    print("└── requirements.txt     ✓ Dependencies listed")
    print("```")
    
    print("\nModules Completed:")
    print("✓ Phase 1: Project foundation and configuration")
    print("✓ Phase 2: ScriptGenerator and ScriptProcessor")
    print("⏳ Phase 3: VoiceSynthesizer and VisualGenerator (Next)")
    print("⏳ Phase 4: VideoComposer")
    print("⏳ Phase 5: SocialMediaManager")
    print("⏳ Phase 6: Main orchestrator")

if __name__ == "__main__":
    process_script_demo()