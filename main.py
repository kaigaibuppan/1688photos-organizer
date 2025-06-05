#!/usr/bin/env python3
"""
Railway deployment entry point - Fixed version
"""
import sys
import os
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """メイン関数"""
    logger.info("🚀 Starting 1688 Photos Organizer")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # ポート設定
    port = int(os.environ.get('PORT', 5000))
    debug = os.getenv('ENVIRONMENT') != 'production'
    
    logger.info(f"🌐 Port: {port}")
    logger.info(f"🔧 Debug mode: {debug}")
    
    try:
        # プロジェクトルートをパスに追加
        sys.path.append(os.path.dirname(__file__))
        
        # web_interfaceをインポート
        logger.info("📦 Importing web interface...")
        from examples.web_interface import app
        
        logger.info("✅ Import successful")
        logger.info(f"🔑 OpenAI configured: {bool(os.getenv('OPENAI_API_KEY'))}")
        
        # Flask アプリ起動
        logger.info("🚀 Starting Flask application...")
        app.run(host='0.0.0.0', port=port, debug=debug)
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        # フォールバック: 最小限のアプリ
        logger.info("🔄 Starting fallback minimal app...")
        start_minimal_app(port)
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        sys.exit(1)

def start_minimal_app(port):
    """フォールバック用最小限アプリ"""
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return '''
        <h1>🚀 1688 Photos Organizer</h1>
        <p>✅ Railway deployment successful</p>
        <p>⚠️ Running in minimal mode</p>
        <p><a href="/health">Health Check</a></p>
        '''
    
    @app.route('/health')
    def health():
        return {"status": "healthy", "mode": "minimal"}
    
    logger.info("🌐 Starting minimal Flask app...")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
