import time
import logging
import json
import random
from datetime import datetime
from typing import Optional

import requests
from telegram import Bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        self.last_success_time = None
        
        # The target URL
        self.target_url = "https://www.sheinindia.in/c/sverse-5939-37961"
        
        # Real browser headers collected from actual browser
        self.headers_list = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
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
        ]
        
        logger.info("=" * 60)
        logger.info("🚀 SHEIN MONITOR STARTED")
        logger.info(f"📊 Target: {self.target_url}")
        logger.info(f"🎯 Threshold: {self.alert_threshold}")
        logger.info(f"⏱️ Check Interval: {self.check_interval}s")
        logger.info("=" * 60)
    
    def extract_men_count_from_html(self, html: str) -> Optional[int]:
        """
        Extract the men's count from HTML
        Looking for pattern: "Men (26)"
        """
        import re
        
        # Method 1: Direct regex for "Men (26)"
        pattern = r'Men\s*\(\s*(\d+)\s*\)'
        matches = re.findall(pattern, html, re.IGNORECASE)
        
        for match in matches:
            if match.isdigit():
                count = int(match)
                logger.debug(f"Found count via regex 'Men (X)': {count}")
                return count
        
        # Method 2: Look for filter data
        # SHEIN often stores filter counts in JSON
        json_patterns = [
            r'"filterCount"\s*:\s*\{[^}]*"men"[^}]*:\s*(\d+)',
            r'"count"\s*:\s*(\d+)[^}]*"name"\s*:\s*"men"',
            r'"Men"\s*:\s*(\d+)',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if match.isdigit():
                    count = int(match)
                    logger.debug(f"Found count via JSON pattern: {count}")
                    return count
        
        # Method 3: Look for product count in page
        product_patterns = [
            r'"productCount"\s*:\s*(\d+)',
            r'"totalCount"\s*:\s*(\d+)',
            r'(\d+)\s+Products?',
            r'Showing\s+(\d+)\s+of',
            r'"numberOfItems"\s*:\s*"(\d+)"',  # Matches "numberOfItems": "295"
        ]
        
        for pattern in product_patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if match.isdigit():
                    count = int(match)
                    logger.debug(f"Found count via product pattern: {count}")
                    return count
        
        return None
    
    def make_request(self):
        """Make HTTP request with proper headers"""
        headers = random.choice(self.headers_list)
        
        # Add cache-busting parameter
        url = f"{self.target_url}?_={int(time.time() * 1000)}"
        
        try:
            # Create a session to handle cookies
            session = requests.Session()
            
            # First, get the homepage to set cookies
            session.get("https://www.sheinindia.in", headers=headers, timeout=10)
            time.sleep(1)
            
            # Now request the actual page
            response = session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully fetched page (Status: {response.status_code})")
                return response.text
            else:
                logger.warning(f"⚠️ Status {response.status_code}, trying alternative method...")
                
                # Try with different approach
                headers['Referer'] = 'https://www.sheinindia.in/'
                headers['Origin'] = 'https://www.sheinindia.in'
                
                response2 = requests.get(self.target_url, headers=headers, timeout=15)
                
                if response2.status_code == 200:
                    return response2.text
                else:
                    logger.error(f"❌ Failed with status {response2.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Request failed: {str(e)}")
            return None
    
    def send_telegram_alert(self, count: int):
        """Send alert to Telegram"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            
            message = f"""
🚨 *SHEINVERSE STOCK ALERT* 🚨

*Men's product count has increased!*

📊 *New Count:* {count}
📈 *Previous Count:* {self.last_count}
🎯 *Threshold:* {self.alert_threshold}
⏰ *Time:* {current_time}

_This is an automated alert from your SHEIN Monitor_
"""
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_notification=False
            )
            
            logger.info(f"📤 Telegram alert sent for count: {count}")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    def perform_check(self, check_number: int):
        """Perform a single check"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 CHECK #{check_number}")
        logger.info(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        # Step 1: Fetch the page
        logger.info("🌐 Fetching page...")
        html = self.make_request()
        
        if not html:
            logger.warning("⚠️ Failed to fetch page, waiting for next check...")
            return
        
        # Step 2: Extract count
        logger.info("🔍 Extracting men's product count...")
        current_count = self.extract_men_count_from_html(html)
        
        if current_count is None:
            logger.warning("⚠️ Could not find men's product count")
            
            # Save HTML for debugging (first 3 failures only)
            if check_number <= 3:
                try:
                    with open(f"debug_{check_number}.html", "w", encoding="utf-8") as f:
                        f.write(html[:50000])  # Save first 50k chars
                    logger.info(f"💾 Saved HTML snippet to debug_{check_number}.html")
                except:
                    pass
            return
        
        # Step 3: Log the result
        logger.info(f"📊 Current Men's Count: {current_count}")
        logger.info(f"📈 Previous Count: {self.last_count}")
        logger.info(f"🎯 Alert Threshold: {self.alert_threshold}")
        
        # Step 4: Check if we need to send alert
        if current_count > self.alert_threshold and current_count > self.last_count:
            logger.info("🚨 ALERT TRIGGERED: Count increased above threshold!")
            self.send_telegram_alert(current_count)
        elif current_count > self.alert_threshold:
            logger.info("ℹ️ Count is above threshold but hasn't increased")
        else:
            logger.info("✅ Count is below threshold")
        
        # Step 5: Update last count
        self.last_count = current_count
        self.last_success_time = datetime.now()
        
        # Step 6: Log to file
        try:
            with open("count_log.csv", "a") as f:
                timestamp = datetime.now().isoformat()
                f.write(f"{timestamp},{current_count}\n")
        except:
            pass
        
        logger.info(f"✅ Check #{check_number} completed successfully")
    
    def run(self):
        """Main monitoring loop"""
        check_number = 0
        consecutive_failures = 0
        
        logger.info("\n" + "="*60)
        logger.info("🏁 MONITORING STARTED - Press Ctrl+C to stop")
        logger.info("="*60)
        
        while True:
            try:
                check_number += 1
                
                self.perform_check(check_number)
                
                # Reset failure counter on success
                consecutive_failures = 0
                
                logger.info(f"⏳ Waiting {self.check_interval} seconds until next check...\n")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Monitoring stopped by user")
                break
                
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"🔥 Error in check #{check_number}: {str(e)}")
                
                # If we have consecutive failures, wait longer
                if consecutive_failures >= 3:
                    wait_time = 30
                    logger.warning(f"⚠️ {consecutive_failures} consecutive failures, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    time.sleep(self.check_interval)

def main():
    """Entry point"""
    monitor = SHEINMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
