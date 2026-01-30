import time
import logging
import json
import random
import re
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
        
        # Proxy settings
        self.proxies = []
        self.proxy_source_url = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
        self.proxy_check_timeout = 10
        
        # The target URL - with filter fragment
        self.target_url = "https://www.sheinindia.in/c/sverse-5939-37961#filterBy"
        
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
                'Referer': 'https://www.sheinindia.in/',
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
                'Referer': 'https://www.sheinindia.in/',
            }
        ]
        
        logger.info("=" * 60)
        logger.info("SHEIN MONITOR STARTED")
        logger.info(f"Target: {self.target_url}")
        logger.info(f"Threshold: {self.alert_threshold}")
        logger.info(f"Check Interval: {self.check_interval}s")
        logger.info("=" * 60)
        
    def fetch_proxies(self):
        """Fetch free proxies from GitHub"""
        try:
            logger.info("Fetching new proxies from GitHub...")
            response = requests.get(self.proxy_source_url, timeout=10)
            if response.status_code == 200:
                proxy_list = response.text.strip().split('\n')
                self.proxies = [p.strip() for p in proxy_list if p.strip()]
                logger.info(f"Fetched {len(self.proxies)} proxies")
                return True
            else:
                logger.warning(f"Failed to fetch proxies: Status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error fetching proxies: {e}")
            return False
    
    def extract_men_count_from_html(self, html: str) -> Optional[int]:
        """
        Extract the men's count from HTML
        Based on the screenshot: "Men (32)"
        """
        try:
            # Method 1: Direct regex for "Men (32)" - exactly as shown in screenshot
            # This pattern matches "Men" followed by space, then parentheses with number
            pattern = r'Men\s*\(\s*(\d+)\s*\)'
            matches = re.findall(pattern, html)
            
            if matches:
                count = int(matches[0])
                logger.info(f"Found men's count via direct pattern: {count}")
                return count
            
            # Method 2: Case-insensitive search for "Men ("
            pattern = r'Men\s*\(\s*(\d+)\s*\)'
            matches = re.findall(pattern, html, re.IGNORECASE)
            
            if matches:
                count = int(matches[0])
                logger.info(f"Found men's count via case-insensitive pattern: {count}")
                return count
            
            # Method 3: Look for filter section that contains "Gender" and "Men"
            # Find the Gender section first
            gender_pattern = r'Gender[^>]*>.*?Men\s*\(\s*(\d+)\s*\)'
            matches = re.findall(gender_pattern, html, re.IGNORECASE | re.DOTALL)
            
            if matches:
                count = int(matches[0])
                logger.info(f"Found men's count in Gender section: {count}")
                return count
            
            # Method 4: Look for list items with "Men ("
            li_pattern = r'<[^>]*>.*?Men\s*\(\s*(\d+)\s*\).*?<'
            matches = re.findall(li_pattern, html, re.IGNORECASE)
            
            if matches:
                count = int(matches[0])
                logger.info(f"Found men's count in list item: {count}")
                return count
            
            # Method 5: Look for the filter count in the filter panel
            # Try to find the filter section by looking for "Filters" text
            filters_pattern = r'Filters[^<]*<[^>]*>.*?Men\s*\(\s*(\d+)\s*\)'
            matches = re.findall(filters_pattern, html, re.IGNORECASE | re.DOTALL)
            
            if matches:
                count = int(matches[0])
                logger.info(f"Found men's count in Filters section: {count}")
                return count
            
            # Debug: Print a snippet of HTML where "Men" appears
            men_index = html.lower().find('men')
            if men_index != -1:
                start = max(0, men_index - 100)
                end = min(len(html), men_index + 200)
                snippet = html[start:end]
                logger.debug(f"HTML snippet around 'Men': {snippet}")
            
            logger.warning("Could not extract men's product count")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting count: {e}")
            return None
    
    def make_request(self):
        """Make HTTP request with rotation and proxies"""
        
        # Ensure we have proxies
        if not self.proxies:
            self.fetch_proxies()
            
        if not self.proxies:
            logger.warning("No proxies available, trying direct connection...")
            # Fallback to direct connection if no proxies
            try:
                headers = random.choice(self.headers_list)
                # Add timestamp to avoid caching
                url = f"{self.target_url.split('#')[0]}?_={int(time.time() * 1000)}"
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                   logger.info(f"Successfully fetched page (Direct) (Status: {response.status_code})")
                   return response.text
                else:
                    logger.warning(f"Direct connection failed with status: {response.status_code}")
            except Exception as e:
                logger.error(f"Direct connection failed: {e}")
            return None

        # Try up to 5 different proxies
        max_attempts = 5
        
        for i in range(max_attempts):
            headers = random.choice(self.headers_list)
            # Add timestamp to avoid caching
            url = f"{self.target_url.split('#')[0]}?_={int(time.time() * 1000)}"
            
            # Pick a random proxy
            proxy_ip = random.choice(self.proxies)
            proxies = {
                "http": f"http://{proxy_ip}",
                "https": f"http://{proxy_ip}"
            }
            
            try:
                logger.info(f"Attempt {i+1}/{max_attempts} using proxy: {proxy_ip}")
                response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
                
                if response.status_code == 200:
                    logger.info(f"Successfully fetched page (Status: {response.status_code})")
                    return response.text
                elif response.status_code in [403, 407, 429]:
                    logger.warning(f"Proxy {proxy_ip} blocked (Status {response.status_code}), trying next...")
                else:
                    logger.warning(f"Status {response.status_code} with proxy {proxy_ip}")
                    
            except Exception as e:
                logger.warning(f"Proxy {proxy_ip} failed: {str(e)}")
                
        logger.error("All proxy attempts failed")
        return None
    
    def send_telegram_alert(self, count: int):
        """Send alert to Telegram"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            
            message = f"""
**SHEINVERSE STOCK ALERT**

Men's product count has changed!

- New Count: {count}  
- Previous Count: {self.last_count}  
- Threshold: {self.alert_threshold}  
- Time: {current_time}  

This is an automated alert from your **SHEIN Monitor**
"""
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_notification=False
            )
            
            logger.info(f"Telegram alert sent for count: {count}")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    def perform_check(self, check_number: int):
        """Perform a single check"""
        logger.info(f"\n{'='*60}")
        logger.info(f"CHECK #{check_number}")
        logger.info(f"{datetime.now().strftime('%H:%M:%S')}")
        
        # Step 1: Fetch the page
        logger.info("Fetching page...")
        html = self.make_request()
        
        if not html:
            logger.warning("Failed to fetch page, waiting for next check...")
            return
        
        # Step 2: Extract count
        logger.info("Extracting men's product count...")
        current_count = self.extract_men_count_from_html(html)
        
        if current_count is None:
            logger.warning("Could not find men's product count")
            
            # Save HTML for debugging (first 3 failures only)
            if check_number <= 3:
                try:
                    with open(f"debug_{check_number}.html", "w", encoding="utf-8") as f:
                        f.write(html[:50000])  # Save first 50k chars
                    logger.info(f"Saved HTML snippet to debug_{check_number}.html")
                except:
                    pass
            return
        
        # Step 3: Log the result
        logger.info(f"Current Men's Count: {current_count}")
        logger.info(f"Previous Count: {self.last_count}")
        logger.info(f"Alert Threshold: {self.alert_threshold}")
        
        # Step 4: Check if we need to send alert
        # Send alert if:
        # 1. Count is above threshold AND
        # 2. Count has changed from previous count
        if current_count > self.alert_threshold and current_count != self.last_count:
            logger.info(f"ALERT TRIGGERED: Count changed from {self.last_count} to {current_count}!")
            self.send_telegram_alert(current_count)
        elif current_count > self.alert_threshold:
            logger.info("Count is above threshold but hasn't changed")
        else:
            logger.info("Count is below threshold")
        
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
        
        logger.info(f"Check #{check_number} completed successfully")
    
    def run(self):
        """Main monitoring loop"""
        check_number = 0
        consecutive_failures = 0
        
        logger.info("\n" + "="*60)
        logger.info("MONITORING STARTED - Press Ctrl+C to stop")
        logger.info("="*60)
        
        while True:
            try:
                check_number += 1
                
                self.perform_check(check_number)
                
                # Reset failure counter on success
                consecutive_failures = 0
                
                logger.info(f"Waiting {self.check_interval} seconds until next check...\n")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("\nMonitoring stopped by user")
                break
                
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Error in check #{check_number}: {str(e)}")
                
                # If we have consecutive failures, wait longer
                if consecutive_failures >= 3:
                    wait_time = 30
                    logger.warning(f"{consecutive_failures} consecutive failures, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    time.sleep(self.check_interval)

def main():
    """Entry point"""
    monitor = SHEINMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
