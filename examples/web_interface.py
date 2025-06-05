from flask import Flask, request, jsonify, render_template_string
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.extractor import Alibaba1688ImageExtractor

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>1688 Image Extractor</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        input[type="url"] { width: 100%; padding: 10px; margin: 10px 0; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; }
        .result { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 1688 商品画像抽出ツール</h1>
        <form id="extractForm">
            <label>商品URL:</label>
            <input type="url" id="productUrl" placeholder="https://detail.1688.com/offer/123456789.html" required>
            <br>
            <label>カスタム指示:</label>
            <textarea id="customInstructions" rows="4" style="width:100%;" placeholder="色別、サイズ別に分類してください..."></textarea>
            <br>
            <button type="submit">画像抽出開始</button>
        </form>
        <div id="result" class="result" style="display:none;"></div>
    </div>

    <script>
        document.getElementById('extractForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = document.getElementById('productUrl').value;
            const instructions = document.getElementById('customInstructions').value;
            
            document.getElementById('result').style.display = 'block';
            document.getElementById('result').innerHTML = '処理中...';
            
            try {
                const response = await fetch('/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url, instructions})
                });
                const data = await response.json();
                document.getElementById('result').innerHTML = `
                    <h3>結果:</h3>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
            } catch (error) {
                document.getElementById('result').innerHTML = `エラー: ${error.message}`;
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    try:
        data = request.get_json()
        url = data.get('url')
        instructions = data.get('instructions', '')
        
        if not url:
            return jsonify({'error': 'URLが必要です'}), 400
        
        extractor = Alibaba1688ImageExtractor()
        results = extractor.process_product(url, instructions)
        extractor.close()
        
        return jsonify({
            'success': True,
            'message': '処理完了',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
