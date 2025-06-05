#!/usr/bin/env python3
"""
Railway deployment entry point - Web Interface
"""
import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(__file__))

if __name__ == '__main__':
    from examples.web_interface import app
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.getenv('ENVIRONMENT') != 'production'
    
    print(f"🚀 Starting 1688 Photos Organizer on Railway")
    print(f"🌐 Port: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
