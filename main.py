import time
import random
import logging
from datetime import datetime
from typing import Optional

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        
        # Proxy list (from your provided list)
        self.proxies = [
            "px711001.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
            "px043006.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
            "px1160303.pointtoserver.com:10780:ppurevpn0s12840722:vkgp6joz",
            "px1400403.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
            "px022409.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
            "px013304.pointtoserver.com:10780:ppurevpn0s12840722:vkgp6joz",
            "px390501.pointtoserver.com:10780:ppurevpn0s12840722:vkgp6joz",
            "px060301.pointtoserver.com:10780:ppurevpn0s12840722:vkgp6joz",
            "px014236.pointtoserver.com:10780:ppurevpn0s12840722:vkgp6joz",
            "px950403.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
            "px340403.pointtoserver.com:10780:purevpn0s12840722:vkgp6joz",
            "px016008.pointtoserver.com:10780:ppurevpn0s12840722:vkgp6joz",
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
        """Setup Chrome driver with random proxy"""
        options = uc.ChromeOptions()
        
        # Headless mode for server
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_argument('--window-size=1920,1080')
        
        # Add proxy if available
        if self.proxies:
            proxy = self.get_next_proxy()
            options.add_argument(f'--proxy-server={proxy["url"]}')
            logger.info(f"Using proxy: {proxy['host']}")
        
        # Setup undetected ChromeDriver
        driver = uc.Chrome(
            options=options,
            version_main=120  # Adjust Chrome version as needed
        )
        
        return driver

    def extract_product_count(self, driver):
        """Extract men's product count from filter panel"""
        try:
            # Look for gender filters
            wait = WebDriverWait(driver, 20)
            
            # Try multiple possible selectors
            possible_selectors = [
                "//div[contains(text(), 'Gender')]/following-sibling::div//span[contains(text(), 'Men')]",
                "//div[contains(@class, 'gender')]//span[contains(text(), 'Men')]",
                "//div[contains(@class, 'filter') and contains(., 'Gender')]//span[contains(text(), 'Men')]",
                "//span[contains(text(), 'Men')]/following-sibling::span",
                "//*[contains(text(), 'Men (')]",
                "//label[contains(text(), 'Men')]"
            ]
            
            for selector in possible_selectors:
                try:
                    element = wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    text = element.text
                    
                    # Extract number from text like "Men (26)"
                    import re
                    match = re.search(r'\((\d+)\)', text)
                    if match:
                        count = int(match.group(1))
                        logger.info(f"Found men's product count: {count}")
                        return count
                except:
                    continue
            
            # If not found, try to find any number next to "Men"
            try:
                elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Men')]")
                for element in elements:
                    text = element.text
                    if '(' in text and ')' in text:
                        import re
                        match = re.search(r'\((\d+)\)', text)
                        if match:
                            count = int(match.group(1))
                            logger.info(f"Found men's product count: {count}")
                            return count
            except:
                pass
                
            logger.warning("Could not find men's product count")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting product count: {str(e)}")
            return None

    def navigate_to_sheinverse(self, driver):
        """Navigate to SHEINVERSE section"""
        try:
            # Open SHEIN homepage
            logger.info("Opening SHEIN homepage...")
            driver.get(self.base_url)
            time.sleep(5)
            
            # Try to accept cookies
            try:
                cookie_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'OK') or contains(text(), 'Got it')]")
                cookie_btn.click()
                time.sleep(2)
            except:
                pass
            
            # Click SHEINVERSE banner/link
            logger.info("Looking for SHEINVERSE banner...")
            
            sheinverse_selectors = [
                "//a[contains(@href, 'sheinverse')]",
                "//*[contains(text(), 'SHEIN VERSE')]",
                "//*[contains(text(), 'SHEINVERSE')]",
                "//div[contains(text(), 'SHEINVERSE')]",
                "//span[contains(text(), 'SHEINVERSE')]"
            ]
            
            for selector in sheinverse_selectors:
                try:
                    element = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    element.click()
                    logger.info("Clicked SHEINVERSE banner")
                    time.sleep(5)
                    break
                except:
                    continue
            
            # Open filter panel
            logger.info("Opening filter panel...")
            filter_selectors = [
                "//button[contains(text(), 'Filter')]",
                "//div[contains(text(), 'Filter')]",
                "//span[contains(text(), 'Filter')]",
                "//*[contains(@class, 'filter') and contains(text(), 'Filter')]"
            ]
            
            for selector in filter_selectors:
                try:
                    filter_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    filter_btn.click()
                    logger.info("Clicked filter button")
                    time.sleep(3)
                    return True
                except:
                    continue
            
            logger.error("Could not find filter button")
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to SHEINVERSE: {str(e)}")
            return False

    def send_telegram_alert(self, count):
        """Send alert via Telegram bot"""
        try:
            message = f"🚨 STOCK ALERT 🚨\n\n"
            message += f"Men's product count in SHEINVERSE: {count}\n"
            message += f"Threshold: {self.alert_threshold}\n"
            message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
            logger.info(f"✅ Telegram alert sent for count: {count}")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {str(e)}")

    def check_once(self):
        """Perform a single check"""
        driver = None
        try:
            logger.info("=" * 50)
            logger.info("Starting new check...")
            
            # Setup driver with proxy
            driver = self.setup_driver()
            
            # Navigate to SHEINVERSE
            if not self.navigate_to_sheinverse(driver):
                logger.error("Failed to navigate, retrying next time")
                if driver:
                    driver.quit()
                return
            
            # Extract product count
            count = self.extract_product_count(driver)
            
            if count is not None:
                logger.info(f"Current count: {count}, Last count: {self.last_count}")
                
                # Send alert if count exceeds threshold and has increased
                if count > self.alert_threshold and count > self.last_count:
                    self.send_telegram_alert(count)
                
                # Update last count
                self.last_count = count
                
                # Take screenshot for debugging
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    driver.save_screenshot(f"screenshot_{timestamp}.png")
                    logger.info(f"Screenshot saved: screenshot_{timestamp}.png")
                except:
                    pass
                    
                return count
            else:
                logger.warning("Could not extract product count")
                return None
                
        except Exception as e:
            logger.error(f"Error during check: {str(e)}")
            return None
            
        finally:
            if driver:
                driver.quit()

    def run_forever(self):
        """Run checks forever every 10 seconds"""
        logger.info("🚀 Starting SHEIN Monitor - Checking every 10 seconds")
        logger.info("Press Ctrl+C to stop")
        
        check_count = 0
        while True:
            try:
                check_count += 1
                logger.info(f"\n📊 Check #{check_count}")
                
                # Perform check
                self.check_once()
                
                # Wait 10 seconds
                logger.info(f"⏳ Waiting 10 seconds until next check...")
                time.sleep(10)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping monitor...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                time.sleep(10)

def main():
    monitor = SHEINMonitor()
    monitor.run_forever()

if __name__ == "__main__":
    main()
