# 改善されたextractor.pyで置き換え
# VSCodeで src/extractor.py を開いて、上記のコードで置き換えてください

# または、GitBashでファイル作成
cat > src/extractor.py << 'EOF'
# 上記の改善されたコードをここに貼り付け
EOF

# プッシュ
git add src/extractor.py
git commit -m "🔥 Major extractor.py improvements

✅ Enhanced Features:
- Cloud environment auto-detection
- Demo mode for Railway/Heroku deployment
- Robust error handling and logging
- Multiple selector fallbacks
- Auto ChromeDriver installation
- Image URL optimization
- File size limits and security

✅ Compatibility:
- Railway/Heroku/Render support
- Selenium optional loading
- OpenAI graceful fallback
- Type hints for better IDE support

✅ Production Ready:
- Comprehensive logging
- Resource cleanup
- Performance optimizations
- Security improvements"

git push origin main