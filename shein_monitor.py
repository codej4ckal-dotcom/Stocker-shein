import time
import logging
import random
import re
import json
from datetime import datetime
from typing import Optional
import urllib3
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

import requests
from telegram import Bot

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Simple HTTP server for health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'OK - SHEIN Monitor is running')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default HTTP logs
        pass

def start_health_server(port=8080):
    """Start a simple HTTP server for health checks"""
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check server started on port {port}")
    server.serve_forever()

class SHEINFilterMonitor:
    def __init__(self):
        # HARDCODED CONFIGURATION - NO ENV VARIABLES
        self.bot_token = "8032399582:AAFzNpKyaxB3sr9gsvmwqGZE_v1m06ij4Rg"
        self.chat_id = "7985177810"
        
        self.bot = Bot(token=self.bot_token)
        
        # Monitoring settings
        self.check_interval = 10  # Check every 10 seconds
        self.alert_threshold = 30  # Alert when count is above 30
        self.last_count = 0
        self.last_success_time = None
        
        # The target URL with filterBy to open filter panel
        self.target_url = "https://www.sheinindia.in/c/sverse-5939-37961#filterBy"
        
        # Cache busting parameters
        self.cache_busting_params = [
            f"?_={int(time.time() * 1000)}",
            f"?timestamp={int(time.time() * 1000)}",
            f"?v={int(time.time())}",
        ]
        
        # Enhanced browser headers specifically for SHEIN India
        self.headers_list = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
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
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            },
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5,hi;q=0.3',
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
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
            }
        ]
        
        logger.info("=" * 60)
        logger.info("🚀 SHEIN FILTER MONITOR STARTED")
        logger.info(f"📌 Target URL: {self.target_url}")
        logger.info(f"🎯 Alert Threshold: {self.alert_threshold}")
        logger.info(f"⏱️ Check Interval: {self.check_interval}s")
        logger.info(f"🤖 Telegram Bot: Active")
        logger.info("=" * 60)
    
    def extract_men_count_from_html(self, html: str) -> Optional[int]:
        """
        Extract men's product count from HTML filter panel
        Based on the pattern: "Men (32)" in the filter section
        """
        try:
            # Method 1: Direct regex for "Men (XX)" - This should be the most reliable
            direct_patterns = [
                r'>\s*Men\s*\(\s*(\d+)\s*\)\s*<',
                r'Men\s*\(\s*(\d+)\s*\)',
                r'\bMen\b[^0-9]*(\d+)[^0-9]*\)',
            ]
            
            for pattern in direct_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    # Take the first match
                    count = int(matches[0])
                    logger.info(f"✅ Found men's count via direct pattern: {count}")
                    return count
            
            # Method 2: Look for Gender filter section
            gender_patterns = [
                r'Gender[^>]*>.*?Men\s*\(\s*(\d+)\s*\)',
                r'<[^>]*data-filter-type=["\']?gender["\'][^>]*>.*?Men\s*\(\s*(\d+)\s*\)',
                r'<[^>]*class=[^>]*filter-item[^>]*>.*?Men.*?\((\d+)\)',
            ]
            
            for pattern in gender_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                if matches:
                    count = int(matches[0])
                    logger.info(f"✅ Found men's count in gender filter: {count}")
                    return count
            
            # Method 3: Look for filter list items
            filter_item_patterns = [
                r'<li[^>]*>.*?Men.*?\((\d+)\).*?</li>',
                r'<div[^>]*>.*?Men.*?\((\d+)\).*?</div>',
                r'<span[^>]*>.*?Men.*?\((\d+)\).*?</span>',
            ]
            
            for pattern in filter_item_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                if matches:
                    count = int(matches[0])
                    logger.info(f"✅ Found men's count in filter item: {count}")
                    return count
            
            # Method 4: Try to find all filter counts and identify men's
            all_filters_pattern = r'([A-Za-z]+)\s*\(\s*(\d+)\s*\)'
            all_matches = re.findall(all_filters_pattern, html)
            
            if all_matches:
                logger.info(f"🔍 Found all filter counts: {all_matches}")
                for filter_name, filter_count in all_matches:
                    if filter_name.lower() == 'men':
                        count = int(filter_count)
                        logger.info(f"✅ Identified men's count from all filters: {count}")
                        return count
            
            # Debug: Try to find any numeric patterns near "Men"
            men_pos = html.lower().find('men')
            if men_pos != -1:
                start = max(0, men_pos - 200)
                end = min(len(html), men_pos + 200)
                context = html[start:end]
                logger.debug(f"🔍 Context around 'Men': {context}")
                
                # Try to extract any number near "Men"
                near_pattern = r'Men[^0-9]*(\d+)'
                near_matches = re.findall(near_pattern, context, re.IGNORECASE)
                if near_matches:
                    count = int(near_matches[0])
                    logger.info(f"✅ Found number near 'Men': {count}")
                    return count
            
            logger.warning("⚠️ Could not extract men's count. HTML structure might have changed.")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting count: {e}")
            return None
    
    def make_request(self):
        """Make HTTP request to fetch the filter page"""
        # Remove fragment for the actual request (server doesn't see #filterBy)
        base_url = self.target_url.split('#')[0]
        cache_param = random.choice(self.cache_busting_params)
        headers = random.choice(self.headers_list)
        
        url = f"{base_url}{cache_param}"
        
        logger.info(f"🌐 Fetching URL: {url[:80]}...")
        
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=15,
                verify=False,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully fetched page (Status: {response.status_code})")
                
                # Check if we got meaningful content
                content_lower = response.text.lower()
                if any(keyword in content_lower for keyword in ['men', 'women', 'gender', 'filter']):
                    return response.text
                else:
                    logger.warning("⚠️ Page fetched but doesn't contain filter keywords")
                    return None
            else:
                logger.warning(f"⚠️ Request failed with status: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("⏰ Request timeout")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("🔌 Connection error")
            return None
        except Exception as e:
            logger.error(f"❌ Request failed: {e}")
            return None
    
    def send_telegram_alert(self, count: int):
        """Send alert to Telegram"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            current_date = datetime.now().strftime("%B %d, %Y")
            
            # Determine change direction
            if self.last_count > 0:
                if count > self.last_count:
                    change_direction = "📈 INCREASED"
                    change_emoji = "🔼"
                elif count < self.last_count:
                    change_direction = "📉 DECREASED"
                    change_emoji = "🔽"
                else:
                    change_direction = "CHANGED"
                    change_emoji = "🔄"
            else:
                change_direction = "DETECTED"
                change_emoji = "🎯"
            
            # Calculate change amount
            change_amount = abs(count - self.last_count) if self.last_count > 0 else 0
            
            message = f"""
🚨 **SHEINVERSE STOCK ALERT** 🚨
{change_emoji} *Men's Product Count {change_direction}*

📊 **Details:**
- New Count: `{count}`
- Previous Count: `{self.last_count}`
- Change: `{f'+{change_amount}' if count > self.last_count else f'-{change_amount}' if self.last_count > 0 else 'N/A'}`
- Threshold: `{self.alert_threshold}`
- Time: `{current_time}`
- Date: `{current_date}`

🔗 **Product Page:**
{self.target_url}

_This is an automated alert from your SHEIN Filter Monitor_
"""
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_notification=False
            )
            
            logger.info(f"✅ Telegram alert sent: {count} (was: {self.last_count})")
            
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert: {e}")
    
    def send_startup_notification(self):
        """Send startup notification to Telegram"""
        try:
            message = f"""
🚀 **SHEIN FILTER MONITOR STARTED** 🚀

✅ **Monitor is now active**
📊 **Monitoring:** Men's product count in SHEINVERSE
🎯 **Alert Threshold:** {self.alert_threshold}+ products
⏱️ **Check Interval:** {self.check_interval} seconds
🔗 **Target URL:** {self.target_url}

_You will receive alerts when the men's product count changes above the threshold._

📅 Started: {datetime.now().strftime('%B %d, %Y %H:%M:%S')}
"""
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_notification=True
            )
            
            logger.info("✅ Startup notification sent")
            
        except Exception as e:
            logger.error(f"❌ Failed to send startup notification: {e}")
    
    def perform_check(self, check_number: int):
        """Perform a single monitoring check"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 CHECK #{check_number}")
        logger.info(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
        
        # Step 1: Fetch the page
        html = self.make_request()
        
        if not html:
            logger.warning("❌ Failed to fetch page, waiting for next check...")
            return
        
        # Step 2: Extract men's product count
        current_count = self.extract_men_count_from_html(html)
        
        if current_count is None:
            logger.warning("❌ Could not extract men's product count")
            return
        
        # Step 3: Log the result
        logger.info(f"📊 Current Men's Count: {current_count}")
        logger.info(f"📊 Previous Count: {self.last_count}")
        logger.info(f"🎯 Alert Threshold: {self.alert_threshold}")
        
        # Step 4: Check if we need to send alert
        # Conditions for alert:
        # 1. Count is above threshold AND count has changed
        # 2. OR count was above threshold and now dropped below (also send alert)
        
        should_alert = False
        alert_reason = ""
        
        if current_count > self.alert_threshold and current_count != self.last_count:
            should_alert = True
            alert_reason = f"Count changed from {self.last_count} to {current_count} (above threshold)"
        elif self.last_count > self.alert_threshold and current_count <= self.alert_threshold:
            should_alert = True
            alert_reason = f"Count dropped below threshold from {self.last_count} to {current_count}"
        
        if should_alert:
            logger.info(f"🚨 ALERT TRIGGERED: {alert_reason}")
            self.send_telegram_alert(current_count)
        else:
            if current_count > self.alert_threshold:
                logger.info("✅ Count is above threshold but unchanged")
            else:
                logger.info(f"📉 Count is at/below threshold: {current_count}")
        
        # Step 5: Update last count
        self.last_count = current_count
        self.last_success_time = datetime.now()
        
        logger.info(f"✅ Check #{check_number} completed successfully")
    
    def run_monitoring(self):
        """Main monitoring loop"""
        check_number = 0
        consecutive_failures = 0
        
        logger.info("\n" + "="*60)
        logger.info("🚀 MONITORING STARTED - Press Ctrl+C to stop")
        logger.info("="*60)
        
        # Send startup notification
        self.send_startup_notification()
        
        try:
            while True:
                try:
                    check_number += 1
                    
                    self.perform_check(check_number)
                    
                    # Reset failure counter on success
                    consecutive_failures = 0
                    
                    # Wait for next check with slight randomization
                    wait_time = self.check_interval + random.uniform(-1, 1)
                    logger.info(f"⏳ Waiting {wait_time:.1f} seconds until next check...\n")
                    time.sleep(wait_time)
                    
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"❌ Error in check #{check_number}: {str(e)}")
                    
                    # If we have consecutive failures, wait longer
                    if consecutive_failures >= 3:
                        wait_time = 30
                        logger.warning(f"⚠️ {consecutive_failures} consecutive failures, waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        time.sleep(self.check_interval)
                        
        except KeyboardInterrupt:
            logger.info("\n🛑 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error in main loop: {e}")
            raise

def main():
    """Entry point"""
    try:
        # Start health check server in a separate thread for Render.com
        port = int(os.getenv('PORT', '8080'))
        health_thread = threading.Thread(target=start_health_server, args=(port,), daemon=True)
        health_thread.start()
        
        # Create and run monitor
        monitor = SHEINFilterMonitor()
        monitor.run_monitoring()
    except Exception as e:
        logger.error(f"❌ Failed to start monitor: {e}")
        raise

if __name__ == "__main__":
    main()
