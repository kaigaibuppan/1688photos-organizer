import requests
import os
import json
import time
from urllib.parse import urljoin, urlparse
from pathlib import Path
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import openai
from PIL import Image
import base64
from io import BytesIO
import yaml
from dotenv import load_dotenv

class Alibaba1688ImageExtractor:
    def __init__(self, config_path="config/config.yaml"):
        """
        1688商品画像抽出・分類ツール
        """
        load_dotenv()  # .envファイルから環境変数読み込み
        
        # 設定ファイル読み込み
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self.get_default_config()
        
        # API key取得
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.openai_client = openai.OpenAI(api_key=api_key)
        self.output_dir = Path(self.config.get('output', {}).get('base_dir', 'extracted_images'))
        self.setup_driver()
        
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
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'output': {
                'base_dir': 'extracted_images',
                'create_metadata': True,
                'image_format': 'jpg',
                'max_images_per_product': 50
            }
        }
        
    def setup_driver(self):
        """Seleniumドライバーの設定"""
        chrome_options = Options()
        if self.config['selenium']['headless']:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"--user-agent={self.config['selenium']['user_agent']}")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def extract_product_info(self, product_url):
        """商品ページから基本情報を抽出"""
        try:
            self.driver.get(product_url)
            time.sleep(3)
            
            # 商品タイトル取得
            title_element = self.driver.find_element(By.CSS_SELECTOR, "h1, .product-title, [class*='title']")
            product_title = title_element.text.strip()
            
            # 商品画像URLを取得
            image_urls = []
            
            # メイン画像
            main_images = self.driver.find_elements(By.CSS_SELECTOR, 
                ".main-image img, .product-image img, [class*='main'] img")
            
            # サムネイル画像
            thumbnail_images = self.driver.find_elements(By.CSS_SELECTOR, 
                ".thumbnail img, .small-img img, [class*='thumb'] img")
            
            # 詳細画像
            detail_images = self.driver.find_elements(By.CSS_SELECTOR, 
                ".detail-image img, [class*='detail'] img")
            
            all_images = main_images + thumbnail_images + detail_images
            
            for img in all_images:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                if src and src.startswith("http"):
                    # 高解像度版のURLに変換
                    high_res_url = self.get_high_resolution_url(src)
                    image_urls.append(high_res_url)
            
            # 重複削除
            image_urls = list(set(image_urls))
            
            return {
                "title": product_title,
                "url": product_url,
                "image_urls": image_urls
            }
            
        except Exception as e:
            print(f"商品情報抽出エラー: {e}")
            return None
    
    def get_high_resolution_url(self, url):
        """画像URLを高解像度版に変換"""
        # 1688の画像URL形式に応じて調整
        if "summ.jpg" in url:
            url = url.replace("summ.jpg", "400x400.jpg")
        elif "_50x50.jpg" in url:
            url = url.replace("_50x50.jpg", "_400x400.jpg")
        elif ".jpg_" in url:
            url = re.sub(r'\.jpg_.*', '.jpg', url)
        
        return url
    
    def download_image(self, url, filepath):
        """画像をダウンロード"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.1688.com/'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:

f.write(response.content)
            
            return True
            
        except Exception as e:
            print(f"画像ダウンロードエラー {url}: {e}")
            return False
    
    def analyze_image_with_openai(self, image_path, custom_instructions=""):
        """OpenAI Vision APIで画像を分析"""
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
                "suggested_folder": "推奨フォルダ名"
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
                max_tokens=self.config['openai']['max_tokens']
            )
            
            # JSONレスポンスをパース
            analysis_text = response.choices[0].message.content
            
            # JSON部分を抽出
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"suggested_folder": "uncategorized", "analysis": analysis_text}
                
        except Exception as e:
            print(f"画像分析エラー {image_path}: {e}")
            return {"suggested_folder": "error", "error": str(e)}
    
    def organize_images(self, product_info, custom_instructions=""):
        """画像をダウンロードして分類"""
        product_title = re.sub(r'[^\w\s-]', '', product_info["title"])[:50]
        base_dir = self.output_dir / product_title
        base_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        for i, image_url in enumerate(product_info["image_urls"]):
            print(f"処理中: 画像 {i+1}/{len(product_info['image_urls'])}")
            
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
                metadata_path = target_dir / f"{final_filename}.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "url": image_url,
                        "analysis": analysis,
                        "timestamp": time.time()
                    }, f, ensure_ascii=False, indent=2)
                
                time.sleep(1)  # API制限対策
        
        return results
    
    def process_product(self, product_url, custom_instructions=""):
        """商品の完全処理"""
        print(f"処理開始: {product_url}")
        
        # 商品情報抽出
        product_info = self.extract_product_info(product_url)
        if not product_info:
            return None
        
        print(f"商品タイトル: {product_info['title']}")
        print(f"画像数: {len(product_info['image_urls'])}")
        
        # 画像整理
        results = self.organize_images(product_info, custom_instructions)
        
        # 全体サマリー保存
        summary_path = self.output_dir / f"{product_info['title'][:50]}" / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                "product_info": product_info,
                "results": results,
                "timestamp": time.time()
            }, f, ensure_ascii=False, indent=2)
        
        print(f"処理完了: {len(results)}枚の画像を分類しました")
        return results
    
    def close(self):
        """リソースのクリーンアップ"""
        if hasattr(self, 'driver'):
            self.driver.quit()

# 使用例
if __name__ == "__main__":
    print("Alibaba1688ImageExtractor クラスが正常に読み込まれました")