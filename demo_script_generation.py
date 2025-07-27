#!/usr/bin/env python3
"""Demo script to show script generation and processing workflow."""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import without going through __init__ to avoid relative import issues
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'models'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'modules'))

from script import Script, ScriptSegment, ScriptStyle
from script_processor import ScriptProcessor


def create_demo_script():
    """Create a demo script to test processing."""
    print("Creating demo script...")
    
    # Create a script object
    script = Script(
        service_name="タニタ公式ネット通販サイト「タニタオンラインショップ」",
        affiliate_url="https://example.com/affiliate/tanita",
        style=ScriptStyle.HUMOROUS,
        title="健康管理が楽しくなる！",
        description="タニタの最新健康機器で、毎日の健康管理をゲーム感覚で楽しもう！"
    )
    
    # Add segments
    segments = [
        ScriptSegment(
            text="みなさん、体重計に乗るのが怖い人〜？はい、私もです！でも、なんと！タニタの体重計なら、乗るのが楽しみになっちゃうんです！",
            duration=8.0,
            visual_description="体重計から逃げる人のアニメーション → タニタの体重計に喜んで乗る人",
            emotion="excited"
        ),
        ScriptSegment(
            text="実は最新のタニタ体組成計、ただの体重計じゃありません。筋肉量、体脂肪率、基礎代謝まで全部わかっちゃう。まるで自分専用のパーソナルトレーナー！",
            duration=10.0,
            visual_description="体組成計の画面に表示される様々な数値のアニメーション",
            emotion="surprised"
        ),
        ScriptSegment(
            text="しかも、スマホアプリと連携して、毎日の変化をグラフで確認。ゲーム感覚で健康管理ができちゃいます。昨日より筋肉量が0.1kg増えた！やったー！みたいな。",
            duration=12.0,
            visual_description="スマホアプリのグラフが上昇するアニメーション、喜ぶキャラクター",
            emotion="happy"
        ),
        ScriptSegment(
            text="今ならタニタオンラインショップで、特別セット販売中！体組成計と活動量計のセットで、24時間あなたの健康をサポート。",
            duration=8.0,
            visual_description="商品セットの画像、価格表示、「特別価格」のバッジ",
            emotion="excited"
        ),
        ScriptSegment(
            text="詳細は概要欄のリンクから！健康は一日にしてならず。でも、楽しく続けられるなら、話は別ですよね？",
            duration=7.0,
            visual_description="「詳細はこちら」ボタン、笑顔のキャラクター",
            emotion="happy"
        )
    ]
    
    for segment in segments:
        script.add_segment(segment)
    
    # Add tags and hashtags
    script.tags = ["タニタ", "健康管理", "体組成計", "ダイエット", "筋トレ", "健康機器"]
    script.hashtags = ["#タニタ", "#健康管理", "#ダイエット", "#体組成計", "#健康習慣"]
    
    print(f"Created script with {len(script.segments)} segments")
    print(f"Total duration: {script.total_duration}s")
    
    return script


def process_demo_script(script):
    """Process the demo script."""
    print("\nProcessing script...")
    
    # Create processor
    processor = ScriptProcessor()
    
    # Process the script
    processed_script = processor.process_script(script)
    
    print(f"Processed script has {len(processed_script.segments)} segments")
    print(f"Adjusted duration: {processed_script.total_duration}s")
    
    # Export for TTS
    tts_segments = processor.export_for_tts(processed_script)
    
    print("\nTTS-ready segments:")
    for i, segment in enumerate(tts_segments):
        print(f"\nSegment {i+1}:")
        print(f"  Text: {segment['text'][:50]}...")
        print(f"  Duration: {segment['duration']:.1f}s")
        print(f"  Emotion: {segment['emotion']}")
        print(f"  Speaking rate: {segment['speaking_rate']}")
    
    # Create summary
    summary = processor.create_script_summary(processed_script)
    
    print("\nScript Summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    return processed_script


def save_demo_output(script):
    """Save the demo output."""
    output_dir = "output/demo"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save script as JSON
    script_path = os.path.join(output_dir, "demo_script.json")
    with open(script_path, 'w', encoding='utf-8') as f:
        json.dump(script.to_dict(), f, ensure_ascii=False, indent=2)
    
    print(f"\nScript saved to: {script_path}")
    
    # Save individual segments
    segments_dir = os.path.join(output_dir, "segments")
    os.makedirs(segments_dir, exist_ok=True)
    
    for i, segment in enumerate(script.segments):
        segment_path = os.path.join(segments_dir, f"segment_{i+1}.json")
        with open(segment_path, 'w', encoding='utf-8') as f:
            json.dump(segment.to_dict(), f, ensure_ascii=False, indent=2)
    
    print(f"Segments saved to: {segments_dir}/")


def main():
    """Run the demo."""
    print("YouTube Shorts Generator - Script Generation Demo")
    print("=" * 50)
    
    try:
        # Create demo script
        script = create_demo_script()
        
        # Process the script
        processed_script = process_demo_script(script)
        
        # Save output
        save_demo_output(processed_script)
        
        print("\n✅ Demo completed successfully!")
        print("\nThis demo shows:")
        print("1. Creating a script with multiple segments")
        print("2. Processing for optimal timing and delivery")
        print("3. Preparing segments for TTS")
        print("4. Generating script summary")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()