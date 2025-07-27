# クイックスタートガイド

YouTube Shortsアフィリエイト動画生成システムの使い方

## 必要な準備

### 1. APIキーの取得

#### Google AI (Gemini) APIキー
1. [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
2. 「Get API key」をクリック
3. 生成されたAPIキーをコピー

**注意**: Gemini APIキー1つでスクリプト生成と音声合成の両方が使用できます！

#### YouTube API認証情報
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成または既存のプロジェクトを選択
3. 「APIとサービス」→「ライブラリ」から「YouTube Data API v3」を検索して有効化
4. 「認証情報」→「認証情報を作成」→「OAuthクライアントID」
5. アプリケーションの種類で「デスクトップアプリ」を選択
6. 作成された認証情報をダウンロード
7. `config/youtube_credentials.json`として保存

### 2. 環境設定

```bash
# .envファイルを作成
cp config/.env.example .env

# .envファイルを編集してAPIキーを設定
# GOOGLE_API_KEY=your_gemini_api_key_here
```

## 最初の動画を作成

### シンプルな例

```bash
# 仮想環境をアクティベート
source venv/bin/activate  # Windows: venv\Scripts\activate

# 動画を生成（自動投稿なし）
python -m src.main "タニタ体重計" "https://affiliate.link/tanita" --style humorous
```

### 生成された動画の確認

生成が完了すると、以下のファイルが作成されます：
- `output/videos/PROJECT_ID/` - 最終的な動画ファイル
- `output/audio/PROJECT_ID/` - 音声ファイル
- `output/visuals/PROJECT_ID/` - 画像素材
- `output/projects/PROJECT_ID/project.json` - プロジェクトファイル

## YouTube投稿

### 初回認証

初めてYouTubeに投稿する際は、ブラウザが開いて認証を求められます：

```bash
# 自動投稿付きで実行
python -m src.main "商品名" "アフィリエイトURL" --auto-post
```

1. ブラウザが自動的に開きます
2. Googleアカウントでログイン
3. 「YouTube Shorts Generator」にアクセスを許可
4. 認証が完了すると、自動的に投稿処理が続行されます

### バッチ処理

複数の動画を一度に作成：

```bash
# examples/batch_services.jsonを編集して商品リストを作成
python -m src.main x x --batch examples/batch_services.json
```

## トラブルシューティング

### よくあるエラー

#### 1. ModuleNotFoundError
```bash
# 依存関係を再インストール
pip install -r requirements.txt
```

#### 2. Google API認証エラー
- APIキーが正しく設定されているか確認
- `.env`ファイルの`GOOGLE_API_KEY`を確認

#### 3. YouTube認証エラー
- `config/youtube_credentials.json`が存在するか確認
- 認証フローを最後まで完了したか確認

#### 4. 音声合成エラー
- GOOGLE_API_KEYが設定されているか確認
- Gemini TTSはスクリプト生成と同じAPIキーを使用

### エラーログの確認

すべてのエラーは`development_errors.log`に記録されます：

```bash
tail -f development_errors.log
```

## 設定のカスタマイズ

`config/default.yaml`を編集して、以下の設定を変更できます：

- AI設定（モデル、温度、トークン数）
- 音声設定（言語、声の種類、速度）
- 動画設定（解像度、FPS、ビットレート）
- YouTube設定（プライバシー、カテゴリー、タグ）

## 次のステップ

1. **スタイルの試行**: `--style`オプションで異なるスタイルを試す
   - `humorous`: ユーモラスな紹介
   - `educational`: 教育的な説明
   - `storytelling`: ストーリー形式
   - `comparison`: 比較レビュー
   - `review`: 詳細レビュー

2. **スケジュール投稿**: 複数の動画を時間差で投稿
   ```bash
   python -m src.main x x --batch services.json --auto-post \
       --schedule-start "2024-02-01T10:00:00" --interval-hours 24
   ```

3. **プロジェクトの再開**: 中断したプロジェクトを再開
   ```bash
   python -m src.main x x --resume output/projects/PROJECT_ID/project.json
   ```