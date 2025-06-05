#!/usr/bin/env python3
"""
Railway用エントリーポイント
"""
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(__file__))

# web_interfaceをインポートして実行
from examples.web_interface import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.getenv('ENVIRONMENT') != 'production'
    
    print(f"🚀 Starting 1688 Photos Organizer on port {port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"🔑 OpenAI API configured: {bool(os.getenv('OPENAI_API_KEY'))}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
