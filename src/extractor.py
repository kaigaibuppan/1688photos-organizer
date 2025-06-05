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
