import time
import random
import logging
from datetime import datetime
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SHEINMonitor:
    def __init__(self):
        # HARDCODED CONFIGURATION
        self.bot_token = "8032399582:AAFzNpKyaxB3sr9gsvmwqGZE_v1m06ij4Rg"
        self.chat_id = "7985177810"
        self.bot = Bot(token=self.bot_token)
        
        # Always check every 10 seconds
        self.check_interval = 10
        
        # Alert when count goes above 30
        self.alert_threshold = 30
        
        # Store last count in memory
        self.last_count = 0
        
        # Proxy list (from your provided list - first 10 for speed)
        self.proxies = [
            "px711001.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
            "px043006.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
            "px1160303.pointtoserver.com:10780:ppurevpn0s12840722:vkgp6joz",
            "px1400403.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
            "px022409.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
        ]
        self.current_proxy_index = 0
        
        # Base URL
        self.base_url = "https://shein.com"
        
        logger.info("SHEIN Monitor initialized - Checking every 10 seconds")
        logger.info(f"Alert threshold: {self.alert_threshold} products")
        logger.info(f"Loaded {len(self.proxies)} proxies for rotation")

    def get_next_proxy(self):
        """Get next proxy in rotation"""
        proxy_str = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        # Parse proxy string
        host, port, username, password = proxy_str.split(':')
        return {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'url': f"http://{username}:{password}@{host}:{port}"
        }

    def setup_driver(self):
        """Setup Chrome driver with proxy"""
        options = Options()
        
        # Headless mode
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--window-size=1920,1080')
        
        # Bypass bot detection
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add proxy if available
        if self.proxies:
            proxy = self.get_next_proxy()
            options.add_argument(f'--proxy-server={proxy["url"]}')
            logger.info(f"Using proxy: {proxy['host']}")
        
        # Use webdriver-manager to handle ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Execute CDP commands to bypass detection
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver

    # [Keep all other methods the same as before...]
    # (extract_product_count, navigate_to_sheinverse, send_telegram_alert, check_once, run_forever)

def main():
    monitor = SHEINMonitor()
    monitor.run_forever()

if __name__ == "__main__":
    main()
