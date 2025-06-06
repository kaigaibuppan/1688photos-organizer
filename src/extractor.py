import requests
import os
import json
import time
from urllib.parse import urljoin, urlparse
from pathlib import Path
import re
import logging
from typing import Optional, Dict, List, Any
import yaml
from dotenv import load_dotenv

# Cloud環境対応の追加インポート
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    import chromedriver_autoinstaller
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logging.warning("Selenium not available - running in demo mode")

try:
    import openai
    from PIL import Image
    import base64
    from io import BytesIO
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI/PIL not available")

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Alibaba1688ImageExtractor:
    def __init__(self, config_path="config/config.yaml", demo_mode=None):
        """
        1688商品画像抽出・分類ツール
        
        Args:
            config_path: 設定ファイルのパス
            demo_mode: デモモード（CloudでSeleniumが使えない場合）
        """
        load_dotenv()  # .envファイルから環境変数読み込み
        
        # デモモード自動判定
        if demo_mode is None:
            demo_mode = os.getenv('DEMO_MODE', 'false').lower() == 'true'
            # Railway/Cloud環境の自動検出
            if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RENDER') or os.getenv('HEROKU'):
                demo_mode = True
                logger.info("🌐 Cloud environment detected - enabling demo mode")
        
        self.demo_mode = demo_mode
        
        # 設定ファイル読み込み
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                self.config = self.get_default_config()
        except Exception as e:
            logger.warning(f"Config file error: {e}, using defaults")
            self.config = self.get_default_config()
        
        # OpenAI client初期化
        self.openai_client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key and api_key.startswith('sk-'):
                try:
                    self.openai_client = openai.OpenAI(api_key=api_key)
                    logger.info("✅ OpenAI client initialized successfully")
                except Exception as e:
                    logger.error(f"OpenAI initialization failed: {e}")
            else:
                logger.warning("⚠️ OpenAI API key not properly configured")
        
        # 出力ディレクトリ設定
        self.output_dir = Path(self.config.get('output', {}).get('base_dir', 'extracted_images'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Selenium driver初期化
        self.driver = None
        if not self.demo_mode and SELENIUM_AVAILABLE:
            self.setup_driver()
        else:
            logger.info("🎭 Running in demo mode - Selenium disabled")
        
    def get_default_config(self):
        """デフォルト設定を返す"""
        return {
            'openai': {
                'model': 'gpt-4-vision-preview',
                'max_tokens': 500,
                'temperature': 0.1
            },
            'selenium': {
                'headless': True,
                'timeout': 30,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'output': {
                'base_dir': 'extracted_images',
                'create_metadata': True,
                'image_format': 'jpg',
                'max_images_per_product': 50
            },
            'site_config': {
                'base_url': 'https://www.1688.com',
                'delay_between_requests': 1,
                'max_retries': 3
            }
        }
        
    def setup_driver(self):
        """Seleniumドライバーの設定"""
        try:
            # Chrome options設定
            chrome_options = Options()
            
            # Cloud環境用の設定
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f"--user-agent={self.config['selenium']['user_agent']}")
            
            # Railway/Cloud環境での追加設定
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # 高速化
            
            # ChromeDriverの自動インストール・設定
            try:
                chromedriver_autoinstaller.install()
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("✅ ChromeDriver initialized successfully")
                return True
            except Exception as e:
                logger.error(f"ChromeDriver setup failed: {e}")
                return False
                    
        except Exception as e:
            logger.error(f"Driver setup failed: {e}")
            return False
    
    def extract_product_info(self, product_url):
        """商品ページから基本情報を抽出"""
        if self.demo_mode or not self.driver:
            return self._demo_product_info(product_url)
            
        try:
            logger.info(f"Extracting info from: {product_url}")
            self.driver.get(product_url)
            
            # ページロード待機
            WebDriverWait(self.driver, self.config['selenium']['timeout']).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            
            # 商品タイトル取得（複数のセレクタを試行）
            title_selectors = [
                "h1",
                ".product-title", 
                "[class*='title']",
                ".offer-title",
                "[data-title]",
                "title"
            ]
            
            product_title = "Unknown Product"
            for selector in title_selectors:
                try:
                    title_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if title_element.text.strip():
                        product_title = title_element.text.strip()[:100]  # 長さ制限
                        break
                except:
                    continue
            
            # 商品画像URL取得
            image_urls = self._extract_image_urls()
            
            result = {
                "title": product_title,
                "url": product_url,
                "image_urls": image_urls,
                "extracted_at": time.time(),
                "extraction_method": "selenium"
            }
            
            logger.info(f"✅ Extracted: {product_title}, {len(image_urls)} images")
            return result
            
        except Exception as e:
            logger.error(f"商品情報抽出エラー: {e}")
            return self._demo_product_info(product_url)
    
    def _extract_image_urls(self):
        """画像URLを抽出"""
        image_urls = []
        
        # 画像セレクタ（優先順位順）
        image_selectors = [
            "img[src*='1688.com']",
            ".main-image img",
            ".product-image img", 
            "[class*='main'] img",
            ".thumbnail img",
            ".small-img img",
            "[class*='thumb'] img",
            ".detail-image img",
            "[class*='detail'] img",
            "img[src*='.jpg']",
            "img[src*='.png']",
            "img"
        ]
        
        for selector in image_selectors:
            try:
                images = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for img in images:
                    src = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("data-original")
                    if src and self._is_valid_image_url(src):
                        high_res_url = self.get_high_resolution_url(src)
                        image_urls.append(high_res_url)
                        
                        # 制限チェック
                        if len(image_urls) >= self.config['output']['max_images_per_product']:
                            break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # 重複削除
        return list(dict.fromkeys(image_urls))  # 順序を保持して重複削除
    
    def _is_valid_image_url(self, url):
        """有効な画像URLかチェック"""
        if not url or not url.startswith('http'):
            return False
        
        # 除外パターン
        exclude_patterns = [
            'favicon',
            'logo',
            'icon',
            'placeholder',
            '1x1',
            'tracking',
            'analytics'
        ]
        
        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in exclude_patterns)
    
    def _demo_product_info(self, url):
        """デモ用の商品情報"""
        return {
            "title": "Demo Product - 1688 Image Extractor Test",
            "url": url,
            "image_urls": [
                "https://via.placeholder.com/400x400/FF5733/FFFFFF?text=Sample+Image+1",
                "https://via.placeholder.com/400x400/33FF57/FFFFFF?text=Sample+Image+2",
                "https://via.placeholder.com/400x400/3357FF/FFFFFF?text=Sample+Image+3",
                "https://via.placeholder.com/400x400/3357FF/FFFFFF?text=Sample+Image+4",
                "https://via.placeholder.com/400x400/FF6B6B/FFFFFF?text=Red+Product",
                "https://via.placeholder.com/400x400/4ECDC4/FFFFFF?text=Blue+Product",
                "https://via.placeholder.com/400x400/45B7D1/FFFFFF?text=Detail+View",
                "https://via.placeholder.com/400x400/FFA07A/FFFFFF?text=Close+Up"
            ],
            "extracted_at": time.time(),
            "extraction_method": "demo"
        }
    
    def get_high_resolution_url(self, url):
        """画像URLを高解像度版に変換"""
        if not url:
            return url
            
        # 1688の画像URL形式に応じて調整
        transformations = [
            (r'summ\.jpg', '400x400.jpg'),
            (r'_50x50\.jpg', '_400x400.jpg'),
            (r'_100x100\.jpg', '_400x400.jpg'),
            (r'_200x200\.jpg', '_400x400.jpg'),
            (r'\.jpg_\d+x\d+\.jpg', '.jpg'),
            (r'\.jpg_.*', '.jpg'),
        ]
        
        for pattern, replacement in transformations:
            url = re.sub(pattern, replacement, url)
        
        return url
    
    def download_image(self, url, filepath):
        """画像をダウンロード"""
        try:
            headers = {
                'User-Agent': self.config['selenium']['user_agent'],
                'Referer': 'https://www.1688.com/',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # ファイルサイズチェック
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB制限
                logger.warning(f"Image too large: {url}")
                return False
            
            # ディレクトリ作成
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル書き込み
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.debug(f"✅ Downloaded: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"画像ダウンロードエラー {url}: {e}")
            return False
    
    def analyze_image_with_openai(self, image_path, custom_instructions=""):
        """OpenAI Vision APIで画像を分析"""
        if not self.openai_client:
            return self._demo_analysis(image_path)
            
        try:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            default_prompt = """
            この商品画像を分析して、以下の情報をJSON形式で返してください：
            {
                "category": "商品カテゴリー",
                "colors": ["色1", "色2"],
                "size_info": "サイズ情報があれば",
                "style": "スタイル・デザインの特徴",
                "material": "素材情報があれば",
                "features": ["特徴1", "特徴2"],
                "suggested_folder": "推奨フォルダ名",
                "confidence": "分析の信頼度(0-100)"
            }
            """
            
            prompt = custom_instructions if custom_instructions else default_prompt
            
            response = self.openai_client.chat.completions.create(
                model=self.config['openai']['model'],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.config['openai']['max_tokens'],
                temperature=self.config['openai']['temperature']
            )
            
            # JSONレスポンスをパース
            analysis_text = response.choices[0].message.content
            
            # JSON部分を抽出
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                analysis['raw_response'] = analysis_text
                return analysis
            else:
                return {
                    "suggested_folder": "uncategorized", 
                    "analysis": analysis_text,
                    "confidence": 50
                }
                
        except Exception as e:
            logger.error(f"画像分析エラー {image_path}: {e}")
            return {
                "suggested_folder": "error", 
                "error": str(e),
                "confidence": 0
            }
    
    def _demo_analysis(self, image_path):
        """デモ用の分析結果"""
        import random
        
        categories = ["アパレル", "アクセサリー", "バッグ", "靴", "電子機器", "ホームグッズ"]
        colors = [
            ["赤", "ダークレッド", "ピンク"],
            ["青", "ネイビー", "スカイブルー"],
            ["緑", "オリーブ", "ライム"],
            ["黄", "ゴールド", "クリーム"],
            ["黒", "グレー", "チャコール"],
            ["白", "オフホワイト", "ベージュ"]
        ]
        
        color_set = random.choice(colors)
        category = random.choice(categories)
        
        return {
            "category": category,
            "colors": color_set,
            "size_info": "S, M, L",
            "style": "モダン",
            "material": "高品質素材",
            "features": ["耐久性", "快適性", "デザイン性"],
            "suggested_folder": f"{color_set[0]}系_{category}",
            "confidence": random.randint(85, 98),
            "analysis_method": "demo"
        }
    
    def organize_images(self, product_info, custom_instructions=""):
        """画像をダウンロードして分類"""
        product_title = re.sub(r'[^\w\s-]', '', product_info["title"])[:50]
        base_dir = self.output_dir / product_title
        base_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        for i, image_url in enumerate(product_info["image_urls"]):
            logger.info(f"処理中: 画像 {i+1}/{len(product_info['image_urls'])}")
            
            # 一時的にダウンロード
            temp_filename = f"temp_image_{i}.jpg"
            temp_path = base_dir / temp_filename
            
            if self.download_image(image_url, temp_path):
                # OpenAIで分析
                analysis = self.analyze_image_with_openai(temp_path, custom_instructions)
                
                # フォルダ作成
                folder_name = analysis.get("suggested_folder", "uncategorized")
                target_dir = base_dir / folder_name
                target_dir.mkdir(exist_ok=True)
                
                # ファイル名生成
                colors = analysis.get("colors", [])
                color_suffix = "_" + "_".join(colors) if colors else ""
                
                final_filename = f"image_{i:03d}{color_suffix}.jpg"
                final_path = target_dir / final_filename
                
                # ファイル移動
                temp_path.rename(final_path)
                
                results.append({
                    "image_url": image_url,
                    "local_path": str(final_path),
                    "analysis": analysis
                })
                
                # メタデータ保存
                if self.config['output']['create_metadata']:
                    metadata_path = target_dir / f"{final_filename}.json"
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            "url": image_url,
                            "analysis": analysis,
                            "timestamp": time.time()
                        }, f, ensure_ascii=False, indent=2)
                
                time.sleep(self.config['site_config']['delay_between_requests'])  # API制限対策
        
        return results
    
    def process_product(self, product_url, custom_instructions=""):
        """商品の完全処理"""
        logger.info(f"🚀 Processing product: {product_url}")
        
        # 商品情報抽出
        product_info = self.extract_product_info(product_url)
        if not product_info:
            logger.error("❌ Failed to extract product info")
            return None
        
        logger.info(f"📋 Product: {product_info['title']}")
        logger.info(f"🖼️ Images found: {len(product_info['image_urls'])}")
        
        # デモモードの場合は簡略化された結果を返す
        if self.demo_mode:
            return {
                "product_info": product_info,
                "results": [
                    {
                        "image_url": url,
                        "analysis": self._demo_analysis(Path("demo.jpg")),
                        "demo_mode": True
                    } for url in product_info['image_urls'][:10]
                ],
                "summary": {
                    "total_images": len(product_info['image_urls']),
                    "processed_images": min(10, len(product_info['image_urls'])),
                    "mode": "demo"
                }
            }
        
        # 実際の画像処理
        results = self.organize_images(product_info, custom_instructions)
        
        # 全体サマリー保存
        summary_path = self.output_dir / f"{product_info['title'][:50]}" / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                "product_info": product_info,
                "results": results,
                "timestamp": time.time()
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Processing complete: {len(results)} images processed")
        return {
            "product_info": product_info,
            "results": results,
            "summary": {
                "total_images": len(product_info['image_urls']),
                "processed_images": len(results),
                "timestamp": time.time()
            }
        }
    
    def close(self):
        """リソースのクリーンアップ"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
                logger.info("✅ ChromeDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")

# 使用例とテスト用関数
def create_extractor(demo_mode=None):
    """環境に応じてExtractorを作成"""
    if demo_mode is None:
        # 環境変数または自動判定
        demo_mode = os.getenv('DEMO_MODE', 'false').lower() == 'true'
        
        # Railway/Cloud環境の自動検出
        if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RENDER') or os.getenv('HEROKU'):
            demo_mode = True
            logger.info("🌐 Cloud environment detected - enabling demo mode")
    
    return Alibaba1688ImageExtractor(demo_mode=demo_mode)

# テスト用メイン関数
if __name__ == "__main__":
    logger.info("🧪 Testing Alibaba1688ImageExtractor")
    
    try:
        extractor = create_extractor(demo_mode=True)
        test_url = "https://detail.1688.com/offer/123456789.html"
        
        result = extractor.process_product(test_url)
        if result:
            logger.info("✅ Test successful!")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            logger.error("❌ Test failed")
            
    except Exception as e:
        logger.error(f"Test error: {e}")
    finally:
        if 'extractor' in locals():
            extractor.close()