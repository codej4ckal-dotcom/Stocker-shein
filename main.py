import time
import logging
from datetime import datetime

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
        
        # Store last count
        self.last_count = 0
        
        logger.info("🚀 SHEIN Monitor Started")
        logger.info(f"Checking every {self.check_interval} seconds")
        logger.info(f"Alert threshold: {self.alert_threshold}")

    def setup_driver(self):
        """Setup Chrome driver"""
        options = Options()
        
        # Headless mode
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Bypass detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # User agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Use webdriver-manager to auto-install correct ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Execute CDP commands
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        return driver

    def extract_men_count(self, driver):
        """Extract men's product count"""
        try:
            # Wait for page to load
            time.sleep(3)
            
            # Try to find men's count
            men_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Men') or contains(text(), 'men')]")
            
            for element in men_elements:
                text = element.text
                if '(' in text and ')' in text:
                    import re
                    match = re.search(r'\((\d+)\)', text)
                    if match:
                        count = int(match.group(1))
                        return count
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting count: {e}")
            return None

    def send_telegram_alert(self, count):
        """Send alert via Telegram"""
        try:
            message = f"🚨 SHEINVERSE STOCK ALERT 🚨\n\n"
            message += f"Men's products: {count}\n"
            message += f"Threshold: {self.alert_threshold}\n"
            message += f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
            
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
            logger.info(f"✅ Telegram alert sent: {count} products")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def check_sheinverse(self):
        """Main check function"""
        driver = None
        try:
            driver = self.setup_driver()
            
            # Open SHEIN
            logger.info("🌐 Opening SHEIN...")
            driver.get("https://shein.com")
            time.sleep(5)
            
            # Look for SHEINVERSE
            logger.info("🔍 Looking for SHEINVERSE...")
            
            # Try different selectors
            sheinverse_selectors = [
                "//*[contains(text(), 'SHEIN VERSE')]",
                "//*[contains(text(), 'SHEINVERSE')]",
                "//a[contains(@href, 'sheinverse')]",
                "//div[contains(text(), 'SHEINVERSE')]"
            ]
            
            found = False
            for selector in sheinverse_selectors:
                try:
                    element = driver.find_element(By.XPATH, selector)
                    element.click()
                    logger.info("✅ Clicked SHEINVERSE")
                    found = True
                    time.sleep(5)
                    break
                except:
                    continue
            
            if not found:
                # Direct URL fallback
                driver.get("https://shein.com/sheinverse")
                logger.info("📝 Using direct URL")
                time.sleep(5)
            
            # Look for filter button
            logger.info("🔍 Opening filters...")
            filter_selectors = [
                "//button[contains(text(), 'Filter')]",
                "//div[contains(text(), 'Filter')]",
                "//span[contains(text(), 'Filter')]"
            ]
            
            for selector in filter_selectors:
                try:
                    element = driver.find_element(By.XPATH, selector)
                    element.click()
                    logger.info("✅ Clicked filter button")
                    time.sleep(3)
                    break
                except:
                    continue
            
            # Extract count
            count = self.extract_men_count(driver)
            
            if count is not None:
                logger.info(f"📊 Current men's product count: {count}")
                
                # Check if we need to alert
                if count > self.alert_threshold and count > self.last_count:
                    self.send_telegram_alert(count)
                
                self.last_count = count
                
                # Save screenshot for debugging
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    driver.save_screenshot(f"check_{timestamp}.png")
                except:
                    pass
                
                return count
            else:
                logger.warning("❌ Could not find men's product count")
                return None
                
        except Exception as e:
            logger.error(f"❌ Check failed: {e}")
            return None
            
        finally:
            if driver:
                driver.quit()

    def run(self):
        """Main loop"""
        check_number = 0
        
        while True:
            try:
                check_number += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"🔄 Check #{check_number}")
                
                result = self.check_sheinverse()
                
                if result is None:
                    logger.warning("⚠️  Check returned no result")
                
                logger.info(f"⏰ Next check in {self.check_interval} seconds...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping monitor...")
                break
            except Exception as e:
                logger.error(f"🔥 Unexpected error: {e}")
                time.sleep(self.check_interval)

def main():
    monitor = SHEINMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
