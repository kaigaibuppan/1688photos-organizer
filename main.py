#!/usr/bin/env python3
import os
import re
from flask import Flask, request, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def extract_1688_images(url, max_images=15):
    """1688商品ページから実際に画像を抽出"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        
        print(f"🔍 Fetching page: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 商品タイトル抽出
        title_selectors = ['h1.d-title', '.d-title', 'h1', '.product-title', '.offer-title']
        product_title = "1688商品"
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                product_title = title_elem.get_text(strip=True)[:50]
                break
        
        print(f"📋 Product title: {product_title}")
        
        # 画像URL抽出
        image_urls = set()
        
        # img タグから抽出
        img_selectors = [
            'img[src*="alicdn.com"]',
            'img[data-src*="alicdn.com"]',
            'img[src*=".jpg"]',
            'img[src*=".png"]',
            'img[src*=".webp"]'
        ]
        
        for selector in img_selectors:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get('src') or img.get('data-src')
                if src and is_valid_image(src):
                    clean_url = clean_image_url(src)
                    if clean_url:
                        image_urls.add(clean_url)
        
        # JavaScript から抽出
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                matches = re.findall(r'"(https?://[^"]*alicdn\.com[^"]*\.(?:jpg|png|webp)[^"]*)"', script.string)
                for match in matches:
                    if is_valid_image(match):
                        clean_url = clean_image_url(match)
                        if clean_url:
                            image_urls.add(clean_url)
        
        # 結果を処理
        image_list = list(image_urls)[:max_images]
        
        enhanced_images = []
        for i, img_url in enumerate(image_list):
            enhanced_images.append({
                'url': enhance_image_quality(img_url),
                'original_url': img_url,
                'index': i + 1,
                'type': classify_image_type(img_url, i)
            })
        
        print(f"🖼️ Found {len(enhanced_images)} images")
        
        return {
            'success': True,
            'title': product_title,
            'url': url,
            'images': enhanced_images,
            'total_found': len(image_urls),
            'extracted_count': len(enhanced_images)
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {'success': False, 'error': f'抽出エラー: {str(e)}'}

def is_valid_image(url):
    """画像として有効かチェック"""
    if not url or not isinstance(url, str):
        return False
    
    if not url.startswith(('http://', 'https://', '//')):
        return False
    
    if not re.search(r'\.(jpg|jpeg|png|webp)', url, re.IGNORECASE):
        return False
    
    exclude_patterns = ['favicon', 'logo', 'icon', '1x1', 'pixel']
    if any(pattern in url.lower() for pattern in exclude_patterns):
        return False
    
    return True

def clean_image_url(url):
    """画像URLをクリーンアップ"""
    if url.startswith('//'):
        url = 'https:' + url
    
    url = url.replace('\\', '')
    
    if '?' in url:
        url = url.split('?')[0]
    
    return url

def enhance_image_quality(url):
    """画像URLを高品質版に変換"""
    if not url:
        return url
    
    # 低解像度を高解像度に変換
    transformations = [
        (r'_50x50\.', '_400x400.'),
        (r'_100x100\.', '_400x400.'),
        (r'_200x200\.', '_400x400.'),
        (r'summ\.jpg', '400x400.jpg'),
    ]
    
    enhanced_url = url
    for pattern, replacement in transformations:
        enhanced_url = re.sub(pattern, replacement, enhanced_url)
    
    return enhanced_url

def classify_image_type(url, index):
    """画像の種類を分類"""
    if index < 3:
        return 'メイン画像'
    elif index < 8:
        return '詳細画像'
    else:
        return 'その他'

# HTMLテンプレート
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 1688 Photos Organizer - 実画像抽出版</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { 
            max-width: 1000px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .success-banner {
            background: linear-gradient(45deg, #28a745, #20c997);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 25px;
            text-align: center;
            font-weight: bold;
        }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #555; }
        input { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #ddd; 
            border-radius: 8px; 
            font-size: 16px;
            box-sizing: border-box;
        }
        button { 
            background: linear-gradient(45deg, #667eea, #764ba2); 
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 8px; 
            font-size: 18px; 
            cursor: pointer; 
            width: 100%;
            transition: all 0.3s;
        }
        button:hover { transform: translateY(-2px); }
        button:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .result { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; }
        .stats-panel {
            background: linear-gradient(45deg, #17a2b8, #007bff);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-around;
            text-align: center;
        }
        .stat-item h3 { margin: 0; font-size: 24px; }
        .stat-item p { margin: 5px 0 0; opacity: 0.9; }
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .image-item {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }
        .image-item:hover { transform: translateY(-5px); }
        .image-item img {
            width: 100%;
            height: 150px;
            object-fit: cover;
            cursor: pointer;
        }
        .image-info { padding: 12px; }
        .image-info h4 { margin: 0 0 5px 0; color: #333; font-size: 14px; }
        .image-info p { margin: 2px 0; color: #666; font-size: 12px; }
        .loading {
            text-align: center;
            padding: 40px;
        }
        .loading::after {
            content: '';
            display: inline-block;
            width: 30px;
            height: 30px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error-box { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; }
        .success-box { background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-banner">
            ✅ 実際の1688画像スクレイピング機能が稼働中！
        </div>
        
        <h1>🚀 1688 Photos Organizer - 実抽出版</h1>
        
        <form id="extractForm">
            <div class="form-group">
                <label for="url">🔗 1688商品URL:</label>
                <input type="url" id="url" 
                       placeholder="https://detail.1688.com/offer/..." 
                       value="https://detail.1688.com/offer/806521859635.html"
                       required>
            </div>
            
            <div class="form-group">
                <label for="maxImages">📊 最大抽出枚数:</label>
                <input type="number" id="maxImages" value="12" min="1" max="30">
            </div>
            
            <button type="submit" id="submitBtn">🚀 実際の画像を抽出開始</button>
        </form>
        
        <div id="result" style="display:none;">
            <h3>📊 抽出結果</h3>
            <div id="resultContent"></div>
        </div>
    </div>

    <script>
        document.getElementById('extractForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const url = document.getElementById('url').value.trim();
            const maxImages = parseInt(document.getElementById('maxImages').value);
            const submitBtn = document.getElementById('submitBtn');
            const resultDiv = document.getElementById('result');
            const resultContent = document.getElementById('resultContent');
            
            if (!url.includes('1688.com')) {
                alert('1688.comのURLを入力してください');
                return;
            }
            
            submitBtn.disabled = true;
            submitBtn.textContent = '🔄 抽出中...';
            resultDiv.style.display = 'block';
            resultContent.innerHTML = '<div class="loading">実際の1688ページから画像を抽出中...</div>';
            
            try {
                const response = await fetch('/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url: url, max_images: maxImages })
                });
                
                const data = await response.json();
                
                if (data.success && data.images && data.images.length > 0) {
                    displayResults(data);
                } else {
                    resultContent.innerHTML = '<div class="error-box">❌ ' + (data.error || '画像が見つかりませんでした') + '</div>';
                }
                
            } catch (error) {
                resultContent.innerHTML = '<div class="error-box">❌ 抽出エラー: ' + error.message + '</div>';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 実際の画像を抽出開始';
            }
        });
        
        function displayResults(data) {
            const resultContent = document.getElementById('resultContent');
            
            let html = '<div class="success-box">✅ ' + data.extracted_count + '枚の画像を抽出しました</div>';
            
            html += '<div class="stats-panel">';
            html += '<div class="stat-item"><h3>' + data.extracted_count + '</h3><p>抽出成功</p></div>';
            html += '<div class="stat-item"><h3>' + data.total_found + '</h3><p>発見総数</p></div>';
            html += '<div class="stat-item"><h3>' + (data.title ? data.title.substring(0, 10) + '...' : 'N/A') + '</h3><p>商品名</p></div>';
            html += '</div>';
            
            html += '<div class="image-grid">';
            data.images.forEach((img, index) => {
                html += '<div class="image-item">';
                html += '<img src="' + img.url + '" alt="商品画像 ' + (index + 1) + '" ';
                html += 'onclick="window.open(\'' + img.url + '\', \'_blank\')" ';
                html += 'onerror="this.style.display=\'none\'">';
                html += '<div class="image-info">';
                html += '<h4>画像 ' + img.index + '</h4>';
                html += '<p>種類: ' + img.type + '</p>';
                html += '</div></div>';
            });
            html += '</div>';
            
            resultContent.innerHTML = html;
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    """実際の1688画像抽出API"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        max_images = int(data.get('max_images', 12))
        
        if not url:
            return jsonify({'success': False, 'error': 'URLが必要です'})
        
        if '1688.com' not in url:
            return jsonify({'success': False, 'error': '1688.comのURLを入力してください'})
        
        print(f"🚀 Starting extraction for: {url}")
        result = extract_1688_images(url, max_images)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify({'success': False, 'error': f'サーバーエラー: {str(e)}'})

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'app': '1688 Photos Organizer - Enhanced Version',
        'version': '2.0.0',
        'features': ['real_scraping', 'image_enhancement']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 Starting 1688 Photos Organizer (Enhanced Version)")
    print(f"🌐 Port: {port}")
    print(f"✅ Real scraping functionality enabled")
    
    app.run(host='0.0.0.0', port=port, debug=False)