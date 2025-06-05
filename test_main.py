from flask import Flask
import os
import sys

print("🚀 Starting Railway Test App...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <h1>🎉 Railway Deployment Success!</h1>
    <p>✅ Flask is running</p>
    <p>✅ Port configuration working</p>
    <p>✅ Python environment operational</p>
    '''

@app.route('/health')
def health():
    return {"status": "healthy", "app": "1688-photos-organizer", "version": "1.0.0"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting Flask app on port {port}")
    print(f"🔗 Health check available at /health")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"❌ Flask startup error: {e}")
        sys.exit(1)
