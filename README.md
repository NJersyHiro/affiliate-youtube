# YouTube Shorts Affiliate Video Generator

最新トレンドのアフィリエイトサービスを面白く紹介するYouTube Shorts動画を自動生成・SNS投稿するシステム。

## 機能

- 🤖 **AIスクリプト生成**: トレンドを意識した魅力的な動画スクリプトを自動生成
- 🎤 **音声合成**: 高品質なTTSエンジンで自然な音声に変換
- 🎥 **動画生成**: 背景、テキスト、アニメーションを統合した動画作成
- 🎬 **自動編集**: 音声と映像を同期し、字幕やBGMを追加
- 📤 **SNS自動投稿**: YouTube Shortsへの自動アップロードと投稿管理

## インストール

```bash
# リポジトリのクローン
git clone https://github.com/NJersyHiro/affiliate-youtube.git
cd affiliate-youtube

# 仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 開発モードでインストール
pip install -e .
```

## セットアップ

1. **必要なAPIキーの取得**
   - **Google AI**: [Google AI Studio](https://makersuite.google.com/app/apikey)でGemini APIキーを取得
   - **YouTube API**: [Google Cloud Console](https://console.cloud.google.com/)でYouTube Data API v3を有効化
   - **TTS API**: Google Cloud TTS、Azure、またはAmazon Pollyのいずれかを設定

2. **環境変数の設定**
   ```bash
   cp config/.env.example .env
   # .envファイルを編集して各種APIキーを設定
   ```

3. **設定ファイルの確認**
   - `config/default.yaml`で詳細設定を調整
   - `config/prompts.yaml`でAIプロンプトをカスタマイズ

## 使用方法

### 基本的な使用

```python
from src.main import YouTubeShortsGenerator

# ジェネレーターの初期化
generator = YouTubeShortsGenerator()

# 動画生成と投稿
result = generator.create_and_post(
    service_name="タニタ公式ネット通販サイト「タニタオンラインショップ」",
    affiliate_url="https://example.com/affiliate/tanita",
    style="humorous",  # ユーモア、educational（教育的）、storytelling（ストーリー）
    auto_post=True
)
```

### コマンドライン使用

```bash
# 基本的な動画生成
python -m src.main "タニタオンラインショップ" "https://example.com/affiliate/tanita"

# 詳細オプション付き
python -m src.main "タニタオンラインショップ" "https://example.com/affiliate/tanita" \
    --style humorous \
    --auto-post \
    --project-name "tanita_campaign"

# バッチ処理
python -m src.main dummy dummy --batch examples/batch_services.json

# スケジュール投稿付きバッチ処理
python -m src.main dummy dummy \
    --batch examples/batch_services.json \
    --auto-post \
    --schedule-start "2024-02-01T10:00:00" \
    --interval-hours 24
```

## プロジェクト構造

```
youtube-shorts-generator/
├── src/
│   ├── main.py                    # メインオーケストレーター
│   ├── modules/                   # コア機能モジュール
│   │   ├── script_generator.py    # AIスクリプト生成
│   │   ├── script_processor.py    # スクリプト分割・処理
│   │   ├── voice_synthesizer.py   # 音声合成（TTS）
│   │   ├── visual_generator.py    # 映像生成
│   │   ├── video_composer.py      # 動画編集・結合
│   │   └── social_media_manager.py # SNS投稿管理
│   ├── utils/                     # ユーティリティ
│   ├── models/                    # データモデル
│   └── templates/                 # テンプレート
├── config/                        # 設定ファイル
├── assets/                        # 素材ファイル
├── output/                        # 出力ディレクトリ
├── tests/                         # テスト
└── docs/                          # ドキュメント
```

## 設定オプション

### AIスクリプト生成設定
- `style`: スクリプトスタイル（humorous/educational/storytelling）
- `max_duration`: 最大動画長（デフォルト60秒）
- `language`: 対象言語（デフォルトja）

### TTS設定
- `voice_id`: 使用する音声ID
- `speed`: 話す速度（0.75-1.25）
- `emotion`: 感情表現（neutral/happy/excited）

### 動画生成設定
- `resolution`: 解像度（1080x1920 for Shorts）
- `fps`: フレームレート（デフォルト30fps）
- `background_style`: 背景スタイル

## 開発

### テストの実行

```bash
# すべてのテスト
pytest

# カバレッジ付き
pytest --cov=src

# 特定のテスト
pytest tests/test_script_generator.py
```

### コードスタイル

```bash
# フォーマット
black src/

# リンティング
flake8 src/

# 型チェック
mypy src/
```

## トラブルシューティング

### APIエラー
- 各APIキーが正しく設定されているか確認
- API使用量の上限とレート制限を確認
- 適切な権限が有効化されているか確認

### 動画生成エラー
- FFmpegが正しくインストールされているか確認
- メモリ不足の場合は解像度を下げる
- GPUを利用できる環境か確認

## 機能の特徴

- **完全自動化**: アフィリエイト情報入力から投稿まで全自動
- **高品質コンテンツ**: AIによる魅力的なスクリプトと自然な音声
- **カスタマイズ可能**: スタイル、音声、ビジュアルを自由に設定
- **スケーラブル**: バッチ処理とクラウド対応

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを作成して変更内容を議論してください。