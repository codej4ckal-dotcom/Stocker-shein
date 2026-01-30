import time
import logging
import re
import random
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from telegram import Bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SHEINMonitor:
    def __init__(self):
        # Telegram Configuration
        self.bot_token = "8032399582:AAFzNpKyaxB3sr9gsvmwqGZE_v1m06ij4Rg"
        self.chat_id = "7985177810"
        self.bot = Bot(token=self.bot_token)
        
        # Monitoring settings
        self.check_interval = 10  # Check every 10 seconds
        self.alert_threshold = 30
        self.last_count = 0
        
        # Target URL - remove #filterBy part
        self.target_url = "https://www.sheinindia.in/c/sverse-5939-37961"
        
        # User agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0'
        ]
        
        # Cookies to mimic real browser
        self.cookies = {
            'country': 'IN',
            'currency': 'INR',
            'language': 'en',
        }
        
        logger.info("✅ SHEIN Monitor Started")
        logger.info(f"🎯 URL: {self.target_url}")
        logger.info(f"📊 Threshold: {self.alert_threshold}")
        logger.info(f"⏱️ Check every: {self.check_interval}s")

    def get_headers(self):
        """Get random headers for each request"""
        return {
            'User-Agent': random.choice(self.user_agents),
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
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.sheinindia.in/',
        }

    def fetch_page(self) -> Optional[str]:
        """Fetch the page with proper headers"""
        try:
            headers = self.get_headers()
            
            logger.info(f"🌐 Fetching: {self.target_url}")
            
            response = requests.get(
                self.target_url,
                headers=headers,
                cookies=self.cookies,
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                logger.info("✅ Page fetched successfully")
                return response.text
            elif response.status_code == 403:
                logger.warning("⚠️ Got 403, trying with different headers...")
                # Try again with more headers
                headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
                headers['Sec-Ch-Ua'] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
                headers['Sec-Ch-Ua-Mobile'] = '?0'
                headers['Sec-Ch-Ua-Platform'] = '"Windows"'
                
                response2 = requests.get(
                    self.target_url,
                    headers=headers,
                    cookies=self.cookies,
                    timeout=30
                )
                
                if response2.status_code == 200:
                    return response2.text
                else:
                    logger.error(f"❌ Still getting {response2.status_code}")
                    return None
            else:
                logger.error(f"❌ HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Fetch error: {str(e)}")
            return None

    def extract_men_count(self, html: str) -> Optional[int]:
        """
        Extract men's count from HTML
        Based on your image: "Men (26)" in filter section
        """
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Method 1: Look for "Men (26)" pattern
        # Search for text containing "Men ("
        import re
        
        # Look for exact pattern "Men (26)"
        men_patterns = [
            r'Men\s*\(\s*(\d+)\s*\)',
            r'Men\s*:\s*(\d+)',
            r'Men.*?(\d+)',
            r'<[^>]*>Men\s*<[^>]*>.*?(\d+)',
        ]
        
        for pattern in men_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if match.isdigit():
                    count = int(match)
                    logger.info(f"🔍 Found count with pattern '{pattern}': {count}")
                    return count
        
        # Method 2: Look for filter items
        # Find all text nodes containing "Men"
        men_elements = soup.find_all(text=lambda text: text and 'Men' in text)
        
        for element in men_elements:
            text = str(element).strip()
            # Look for "Men (26)" pattern
            match = re.search(r'Men\s*\((\d+)\)', text)
            if match:
                count = int(match.group(1))
                logger.info(f"🔍 Found in filter element: {count}")
                return count
            
            # Also check parent for count
            parent = element.parent
            if parent:
                parent_text = parent.get_text()
                match = re.search(r'Men.*?(\d+)', parent_text)
                if match:
                    count = int(match.group(1))
                    logger.info(f"🔍 Found in parent: {count}")
                    return count
        
        # Method 3: Save HTML for debugging
        logger.warning("⚠️ Could not find men's count")
        # Uncomment to debug
        # with open("debug_page.html", "w", encoding="utf-8") as f:
        #     f.write(html)
        # logger.info("📁 Saved HTML to debug_page.html")
        
        return None

    def send_alert(self, count: int):
        """Send Telegram alert"""
        try:
            message = f"""
🚨 *SHEINVERSE ALERT* 🚨

Men's product count has changed!

📈 *New Count:* {count}
📊 *Previous:* {self.last_count}
🎯 *Threshold:* {self.alert_threshold}
⏰ *Time:* {datetime.now().strftime('%H:%M:%S')}
📅 *Date:* {datetime.now().strftime('%Y-%m-%d')}

_Count exceeded {self.alert_threshold} threshold_
"""
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"📤 Alert sent: {count} products")
        except Exception as e:
            logger.error(f"❌ Failed to send alert: {e}")

    def check_once(self):
        """Perform a single check"""
        logger.info("─" * 50)
        logger.info("🔄 Checking...")
        
        # Get page
        html = self.fetch_page()
        
        if not html:
            logger.warning("⚠️ No HTML, skipping check")
            return
        
        # Extract count
        current_count = self.extract_men_count(html)
        
        if current_count is None:
            logger.warning("⚠️ Could not extract count")
            return
        
        # Log current status
        logger.info(f"📊 Current: {current_count} | Last: {self.last_count} | Threshold: {self.alert_threshold}")
        
        # Check conditions for alert
        if current_count > self.alert_threshold and current_count > self.last_count:
            logger.info("🚨 ALERT: Count increased above threshold!")
            self.send_alert(current_count)
        elif current_count > self.alert_threshold:
            logger.info("ℹ️ Above threshold but no increase")
        else:
            logger.info("✅ Below threshold")
        
        # Update last count
        self.last_count = current_count
        
        # Log to file
        try:
            with open("count_history.txt", "a") as f:
                f.write(f"{datetime.now().isoformat()},{current_count}\n")
        except:
            pass

    def run(self):
        """Main loop"""
        logger.info("""
┌──────────────────────────────────────────┐
│         SHEIN MONITOR RUNNING           │
│    Checking men's product count         │
│    Threshold: 30                        │
│    Check interval: 10 seconds           │
│    Press Ctrl+C to stop                 │
└──────────────────────────────────────────┘
        """)
        
        check_num = 0
        
        while True:
            try:
                check_num += 1
                logger.info(f"\n🔢 Check #{check_num}")
                
                self.check_once()
                
                logger.info(f"⏳ Next check in {self.check_interval}s...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopped by user")
                break
            except Exception as e:
                logger.error(f"🔥 Error: {e}")
                time.sleep(self.check_interval)

def main():
    monitor = SHEINMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
