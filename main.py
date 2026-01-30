import time
import re
import logging
import random
from datetime import datetime
from typing import Optional

import requests
import cloudscraper
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from telegram import Bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SHEINMonitor:
    def __init__(self):
        # Telegram Configuration (your credentials)
        self.bot_token = "8032399582:AAFzNpKyaxB3sr9gsvmwqGZE_v1m06ij4Rg"
        self.chat_id = "7985177810"
        self.bot = Bot(token=self.bot_token)
        
        # Monitoring settings
        self.check_interval = 10  # Check every 10 seconds
        self.alert_threshold = 30
        self.last_count = 0
        
        # The direct URL that shows the count
        self.target_url = "https://www.sheinindia.in/c/sverse-5939-37961#filterBy"
        
        # Create scraper to bypass Cloudflare
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            },
            delay=10
        )
        
        # User agent rotation
        self.ua = UserAgent()
        
        # Proxy list (simplified - using first 5 proxies)
        self.proxies = [
            "http://purevpn0s12840722:vkgp6joz@px711001.pointtoserver.com:10780",
            "http://purevpn0s12840722:vkgp6joz@px043006.pointtoserver.com:10780",
            "http://ppurevpn0s12840722:vkgp6joz@px1160303.pointtoserver.com:10780",
            "http://purevpn0s12840722:vkgp6joz@px1400403.pointtoserver.com:10780",
            "http://purevpn0s12840722:vkgp6joz@px022409.pointtoserver.com:10780",
        ]
        self.current_proxy_index = 0
        
        logger.info("✅ SHEIN Monitor Initialized")
        logger.info(f"🎯 Target URL: {self.target_url}")
        logger.info(f"📊 Alert Threshold: {self.alert_threshold}")
        logger.info(f"⏱️  Check Interval: {self.check_interval} seconds")

    def get_next_proxy(self) -> dict:
        """Get next proxy in rotation"""
        proxy_url = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return {"http": proxy_url, "https": proxy_url}

    def fetch_page(self) -> Optional[str]:
        """Fetch the page HTML with proxy rotation"""
        proxy = self.get_next_proxy()
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        
        try:
            logger.info(f"🌐 Fetching page using proxy: {proxy['http'].split('@')[1]}")
            
            response = self.scraper.get(
                self.target_url,
                headers=headers,
                proxies=proxy,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("✅ Page fetched successfully")
                return response.text
            else:
                logger.error(f"❌ HTTP {response.status_code}: Failed to fetch page")
                return None
                
        except Exception as e:
            logger.error(f"❌ Request failed: {str(e)}")
            return None

    def extract_product_count(self, html: str) -> Optional[int]:
        """
        Extract product count from the HTML
        This is the main logic - we look for the product count in different ways
        """
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # STRATEGY 1: Look for filter counts (most common)
        # SHEIN usually shows count in filter buttons like "Men (26)"
        filter_items = soup.find_all(['a', 'span', 'div', 'li'], class_=lambda x: x and 'filter' in x.lower())
        
        for item in filter_items:
            text = item.get_text(strip=True)
            # Look for patterns like: Men (26), Men 26, Men:26
            match = re.search(r'Men\s*[\(\:]?\s*(\d+)\s*[\)]?', text, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                logger.info(f"📌 Found count in filter: {count}")
                return count
        
        # STRATEGY 2: Look for product count display
        # Common selectors used by SHEIN
        count_selectors = [
            '.product-count',
            '.goods-num',
            '.total-products',
            '.item-count',
            '.j-expose__product-count',
            '[data-count]',
            '.search-count',
            '.j-search-count',
        ]
        
        for selector in count_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                # Extract numbers from text
                numbers = re.findall(r'\d+', text)
                if numbers:
                    count = int(numbers[0])
                    logger.info(f"📌 Found count via selector {selector}: {count}")
                    return count
        
        # STRATEGY 3: Look in page title/header
        title_elements = soup.find_all(['h1', 'h2', 'title', 'span'], string=lambda t: t and 'product' in t.lower())
        for element in title_elements:
            text = element.get_text()
            numbers = re.findall(r'\d+', text)
            if numbers:
                count = int(numbers[0])
                logger.info(f"📌 Found count in title: {count}")
                return count
        
        # STRATEGY 4: Search entire HTML for common patterns
        patterns = [
            r'"totalCount"\s*:\s*(\d+)',
            r'"productCount"\s*:\s*(\d+)',
            r'"count"\s*:\s*(\d+)',
            r'Showing\s+(\d+)\s+products',
            r'(\d+)\s+products',
            r'(\d+)\s+items',
            r'Total\s*:\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if match.isdigit():
                    count = int(match)
                    logger.info(f"📌 Found count via regex {pattern}: {count}")
                    return count
        
        # STRATEGY 5: Try to count product items on page
        product_items = soup.select('.S-product-item, .j-product-item, .c-product, .product-card')
        if product_items:
            logger.info(f"📌 Found {len(product_items)} product items on page")
            # Note: This might not be total count (due to pagination)
            # But if other methods fail, this gives us something
        
        logger.warning("⚠️ Could not find product count in HTML")
        
        # Save HTML for debugging (only first time)
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("📁 Saved HTML to debug_page.html for inspection")
        
        return None

    def send_telegram_alert(self, count: int):
        """Send alert to Telegram"""
        try:
            message = f"""
🚨 *SHEINVERSE STOCK ALERT* 🚨

Men's product count has increased!

📊 *Current Count:* {count}
📈 *Previous Count:* {self.last_count}
🎯 *Threshold:* {self.alert_threshold}
⏰ *Time:* {datetime.now().strftime('%H:%M:%S')}

_This is an automated alert from SHEIN Monitor_
"""
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"📤 Telegram alert sent for count: {count}")
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert: {str(e)}")

    def perform_check(self):
        """Perform a single check cycle"""
        logger.info("=" * 60)
        logger.info("🔄 Starting check...")
        
        # Step 1: Fetch the page
        html = self.fetch_page()
        
        if not html:
            logger.warning("⚠️ Skipping check due to fetch failure")
            return
        
        # Step 2: Extract product count
        current_count = self.extract_product_count(html)
        
        if current_count is None:
            logger.warning("⚠️ Could not extract product count")
            return
        
        # Step 3: Log current status
        logger.info(f"📊 Current Count: {current_count}")
        logger.info(f"📈 Previous Count: {self.last_count}")
        logger.info(f"🎯 Threshold: {self.alert_threshold}")
        
        # Step 4: Check if alert is needed
        if current_count > self.alert_threshold and current_count > self.last_count:
            logger.info("🚨 ALERT: Count exceeds threshold and increased!")
            self.send_telegram_alert(current_count)
        elif current_count > self.alert_threshold:
            logger.info("ℹ️ Count exceeds threshold but hasn't increased")
        else:
            logger.info("✅ Count is below threshold")
        
        # Step 5: Update last count
        self.last_count = current_count
        
        # Step 6: Save for debugging (optional)
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(f"count_log.txt", "a") as f:
                f.write(f"{timestamp},{current_count}\n")
        except:
            pass

    def run_forever(self):
        """Main monitoring loop"""
        logger.info("""
╔══════════════════════════════════════════════════╗
║           SHEIN MONITOR STARTED                 ║
║        Direct URL: sheinindia.in/sverse        ║
║        Checking every 10 seconds                ║
║        Press Ctrl+C to stop                     ║
╚══════════════════════════════════════════════════╝
        """)
        
        check_number = 0
        
        while True:
            try:
                check_number += 1
                logger.info(f"\n📋 Check #{check_number}")
                
                self.perform_check()
                
                logger.info(f"⏳ Waiting {self.check_interval} seconds...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"🔥 Unexpected error: {str(e)}")
                logger.info("🔄 Retrying in 10 seconds...")
                time.sleep(self.check_interval)

def main():
    """Main entry point"""
    monitor = SHEINMonitor()
    monitor.run_forever()

if __name__ == "__main__":
    main()
