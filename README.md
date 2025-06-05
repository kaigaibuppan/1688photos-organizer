# 1688商品画像抽出・AI分類ツール

中国アリババ（1688.com）の商品ページから画像を自動抽出し、OpenAI GPT-4 Visionを使用して智能分類するツールです。

## 🚀 機能

- ✅ 1688商品ページからの画像自動抽出
- ✅ OpenAI GPT-4 Visionによる画像分析
- ✅ 色・サイズ・カテゴリ別自動フォルダ分類
- ✅ 高解像度画像の取得
- ✅ メタデータの自動保存

## 📦 インストール

\`\`\`bash
# リポジトリクローン
git clone https://github.com/yourusername/alibaba-image-extractor.git
cd alibaba-image-extractor

# 依存関係インストール
pip install -r requirements.txt

# 環境設定
cp .env.example .env
# .envファイルにOpenAI APIキーを設定
\`\`\`

## 🔧 使用方法

\`\`\`python
from src.extractor import Alibaba1688ImageExtractor

extractor = Alibaba1688ImageExtractor()
results = extractor.process_product("https://detail.1688.com/offer/123456789.html")
\`\`\`

詳細は [docs/usage.md](docs/usage.md) を参照してください。# 1688photos-organizer
1688商品画像抽出・AI分類ツール
