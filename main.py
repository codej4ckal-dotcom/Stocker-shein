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
        
        # Use the provided working proxies
        self.proxies = [
            "http://KUW13c1nFxecEKhE:UHaoOIMWnpwHOU2a@geo.g-w.info:10080",
            "http://huCj0gKecBHifYVC:8nrCaEUR8t2C5Llk@geo.g-w.info:10080",
            "http://mMQoZnGSy8kIrFul:v43gVbFPd7lfBa5M@geo.g-w.info:10080",
            "http://JbaLqkX6Rdq2MBrn:anXnVfjfJIs7d05j@geo.g-w.info:10080",
            "http://FEasPUIMSeDrZtjB:aFnjp2YKIZk7gKPJ@geo.g-w.info:10080",
            "http://2xt-customer-xi4tcsT0Vtt-proxy-anuz:17q5yrumu1d@proxy.2extract.net:5555",
            "http://ebQWGfx9n1oQlhQK:WAaWggoEKe1G576O@geo.g-w.info:10080",
            "http://P5oHRYHqX3w8yQhq:yoOlnnpQ3dDcIlLX@geo.g-w.info:10080"
        ]
        
        logger.info(f"Loaded {len(self.proxies)} working proxies")
        
        # The target URL - using filterBy to show filter panel
        self.target_url = "https://www.sheinindia.in/c/sverse-5939-37961"
        
        # Enhanced headers with better browser emulation
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
                'Accept-Charset': 'utf-8',
            },
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
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
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://www.sheinindia.in/',
            }
        ]
        
        # Add cache-busting parameters to avoid cached responses
        self.cache_busting_params = [
            f"?_={int(time.time() * 1000)}",
            f"?timestamp={int(time.time() * 1000)}",
            f"?nocache={int(time.time() * 1000)}",
            f"?v={int(time.time() * 1000)}",
        ]
        
        logger.info("=" * 60)
        logger.info("SHEIN MONITOR STARTED")
        logger.info(f"Target: {self.target_url}")
        logger.info(f"Threshold: {self.alert_threshold}")
        logger.info(f"Check Interval: {self.check_interval}s")
        logger.info(f"Loaded {len(self.proxies)} proxies")
        logger.info("=" * 60)
    
    def extract_men_count_from_html(self, html: str) -> Optional[int]:
        """
        Extract the men's count from HTML
        Based on the screenshot: "Men (32)"
        """
        try:
            # Clean the HTML - remove newlines and extra spaces for better regex matching
            cleaned_html = html.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            
            # Method 1: Direct regex for "Men (32)" - exact match
            # This is the primary method based on your screenshot
            pattern = r'Men\s*\(\s*(\d+)\s*\)'
            matches = re.findall(pattern, cleaned_html)
            
            if matches:
                # Take the first match (should be the men's count)
                count = int(matches[0])
                logger.info(f"✓ Found men's count: {count}")
                return count
            
            # Method 2: Look for gender filter section
            # Find the Gender section and extract men's count from it
            gender_pattern = r'Gender[^>]*>.*?Men\s*\(\s*(\d+)\s*\)'
            matches = re.findall(gender_pattern, cleaned_html, re.IGNORECASE | re.DOTALL)
            
            if matches:
                count = int(matches[0])
                logger.info(f"✓ Found in Gender section: {count}")
                return count
            
            # Method 3: Look for filter item with men count
            # Search for list items or spans containing Men with count
            filter_patterns = [
                r'<[^>]*data-filter-name=["\']?men["\'][^>]*>.*?\((\d+)\)',
                r'<[^>]*class=[^>]*filter-item[^>]*>.*?Men.*?\((\d+)\)',
                r'<[^>]*>Men.*?\((\d+)\)<',
                r'Men["\'\s].*?(\d+).*?\)',
            ]
            
            for pattern in filter_patterns:
                matches = re.findall(pattern, cleaned_html, re.IGNORECASE)
                if matches:
                    count = int(matches[0])
                    logger.info(f"✓ Found via filter pattern: {count}")
                    return count
            
            # Method 4: Try to find the filter count in JSON data
            # Look for JSON structures that might contain filter counts
            json_patterns = [
                r'"filterCount"\s*:\s*\{[^}]*"men"\s*:\s*(\d+)',
                r'"men"\s*:\s*(\d+)[^}]*"filterCount"',
                r'"gender"[^}]*"men"\s*:\s*(\d+)',
                r'"Men"\s*:\s*(\d+)',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, cleaned_html, re.IGNORECASE)
                if matches:
                    count = int(matches[0])
                    logger.info(f"✓ Found in JSON data: {count}")
                    return count
            
            # Debug: Save HTML snippet for analysis
            logger.warning("Could not extract men's count with primary methods")
            
            # Try to find any mention of Men with numbers
            debug_pattern = r'Men[^0-9]*(\d+)'
            debug_matches = re.findall(debug_pattern, cleaned_html, re.IGNORECASE)
            if debug_matches:
                logger.warning(f"Debug - Found potential counts near 'Men': {debug_matches}")
            
            # Also look for Women count to verify we're in the right section
            women_pattern = r'Women\s*\(\s*(\d+)\s*\)'
            women_matches = re.findall(women_pattern, cleaned_html, re.IGNORECASE)
            if women_matches:
                logger.warning(f"Found Women count: {women_matches[0]}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting count: {e}")
            return None
    
    def make_request(self):
        """Make HTTP request with proxy rotation and headers"""
        
        # Rotate through different cache-busting parameters
        cache_param = random.choice(self.cache_busting_params)
        
        # Try up to 3 different proxies
        max_attempts = 3
        
        for i in range(max_attempts):
            # Randomly select headers and proxy
            headers = random.choice(self.headers_list)
            proxy = random.choice(self.proxies)
            
            # Build URL with cache busting
            url = f"{self.target_url}{cache_param}"
            
            # Setup proxies dict
            proxies = {
                "http": proxy,
                "https": proxy.replace('http://', 'https://') if proxy.startswith('http://') else proxy
            }
            
            try:
                logger.info(f"Attempt {i+1}/{max_attempts} using proxy: {proxy[:50]}...")
                
                # Add a small random delay between requests
                time.sleep(random.uniform(0.5, 1.5))
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    proxies=proxies, 
                    timeout=15,
                    verify=False  # Sometimes needed with proxies
                )
                
                if response.status_code == 200:
                    # Check if the response contains the expected content
                    if 'Men' in response.text or 'Women' in response.text or 'Gender' in response.text:
                        logger.info(f"✓ Successfully fetched page (Status: {response.status_code})")
                        return response.text
                    else:
                        logger.warning("Page fetched but doesn't contain expected filter content")
                elif response.status_code in [403, 429, 503]:
                    logger.warning(f"Proxy blocked/rate limited (Status {response.status_code})")
                else:
                    logger.warning(f"Status {response.status_code}")
                    
            except requests.exceptions.ConnectTimeout:
                logger.warning(f"Proxy timeout: {proxy[:50]}...")
            except requests.exceptions.ProxyError:
                logger.warning(f"Proxy error: {proxy[:50]}...")
            except Exception as e:
                logger.warning(f"Request failed: {str(e)[:100]}")
        
        # Fallback: Try direct connection as last resort
        logger.warning("All proxy attempts failed, trying direct connection...")
        try:
            headers = random.choice(self.headers_list)
            url = f"{self.target_url}{cache_param}"
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                logger.info(f"✓ Direct connection successful")
                return response.text
        except Exception as e:
            logger.error(f"Direct connection also failed: {e}")
        
        return None
    
    def send_telegram_alert(self, count: int, change_type: str = "changed"):
        """Send alert to Telegram"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            date_str = datetime.now().strftime("%B %d")
            
            # Determine change direction
            if self.last_count > 0:
                if count > self.last_count:
                    change_direction = "increased"
                elif count < self.last_count:
                    change_direction = "decreased"
                else:
                    change_direction = "unchanged"
            else:
                change_direction = "detected"
            
            message = f"""
**SHEINVERSE STOCK ALERT - {date_str}**

Men's product count has {change_direction}!

- New Count: `{count}`  
- Previous Count: `{self.last_count}`  
- Threshold: `{self.alert_threshold}`  
- Time: `{current_time}`  

_This is an automated alert from your SHEIN Monitor_
"""
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_notification=False
            )
            
            logger.info(f"✓ Telegram alert sent: {count} (was: {self.last_count})")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    def perform_check(self, check_number: int):
        """Perform a single check"""
        logger.info(f"\n{'='*60}")
        logger.info(f"CHECK #{check_number}")
        logger.info(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        
        # Step 1: Fetch the page
        html = self.make_request()
        
        if not html:
            logger.warning("✗ Failed to fetch page")
            return
        
        # Step 2: Extract count
        current_count = self.extract_men_count_from_html(html)
        
        if current_count is None:
            logger.warning("✗ Could not find men's product count")
            
            # Save HTML for debugging (first 5 failures)
            if check_number <= 5:
                try:
                    filename = f"debug_check_{check_number}_{int(time.time())}.html"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(html[:20000])  # Save first 20k chars
                    logger.info(f"Saved debug HTML to {filename}")
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
        # 2. Count is different from previous count
        if current_count > self.alert_threshold and current_count != self.last_count:
            logger.info(f"✓ ALERT TRIGGERED: Count {change_direction} from {self.last_count} to {current_count}")
            self.send_telegram_alert(current_count)
        elif current_count > self.alert_threshold:
            logger.info("Count is above threshold but unchanged")
        elif current_count <= self.alert_threshold:
            logger.info(f"Count is below/at threshold: {current_count}")
            
            # Also send alert if it was previously above threshold and now dropped below
            if self.last_count > self.alert_threshold and current_count <= self.alert_threshold:
                logger.info(f"✓ ALERT: Count dropped below threshold from {self.last_count} to {current_count}")
                self.send_telegram_alert(current_count)
        
        # Step 5: Update last count
        self.last_count = current_count
        self.last_success_time = datetime.now()
        
        # Step 6: Log to file for tracking
        try:
            with open("shein_monitor_log.csv", "a", encoding="utf-8") as f:
                timestamp = datetime.now().isoformat()
                f.write(f"{timestamp},{current_count},{self.last_count}\n")
        except Exception as e:
            logger.warning(f"Could not write to log file: {e}")
        
        logger.info(f"✓ Check #{check_number} completed")
    
    def run(self):
        """Main monitoring loop"""
        check_number = 0
        consecutive_failures = 0
        
        logger.info("\n" + "="*60)
        logger.info("MONITORING STARTED - Press Ctrl+C to stop")
        logger.info("="*60)
        
        # Send startup notification
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text="🚀 SHEIN Monitor started successfully!\nMonitoring for men's product count changes above 30.",
                parse_mode='Markdown'
            )
        except:
            pass
        
        while True:
            try:
                check_number += 1
                
                self.perform_check(check_number)
                
                # Reset failure counter on success
                consecutive_failures = 0
                
                # Randomize wait time slightly to avoid patterns
                wait_time = self.check_interval + random.uniform(-2, 2)
                logger.info(f"Waiting {wait_time:.1f} seconds until next check...\n")
                time.sleep(wait_time)
                
            except KeyboardInterrupt:
                logger.info("\nMonitoring stopped by user")
                # Send shutdown notification
                try:
                    self.bot.send_message(
                        chat_id=self.chat_id,
                        text="🛑 SHEIN Monitor stopped.",
                        parse_mode='Markdown'
                    )
                except:
                    pass
                break
                
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Error in check #{check_number}: {str(e)}")
                
                # If we have consecutive failures, wait longer
                if consecutive_failures >= 3:
                    wait_time = 60
                    logger.warning(f"{consecutive_failures} consecutive failures, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    time.sleep(self.check_interval)

def main():
    """Entry point"""
    monitor = SHEINMonitor()
    monitor.run()

if __name__ == "__main__":
    # Disable SSL warnings for proxy connections
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main()
