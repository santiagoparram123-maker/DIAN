import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def debug_bdme():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    print("Navigating to URL...")
    driver.get("https://www.chip.gov.co/schip_rt/index.jsf")
    time.sleep(3)
    
    print("Page Title:", driver.title)
    # Check if there are frames
    frames = driver.find_elements(by="tag name", value="frame")
    iframes = driver.find_elements(by="tag name", value="iframe")
    print(f"Frames: {len(frames)}, Iframes: {len(iframes)}")
    
    print("HTML Snippet:")
    print(driver.page_source[:1000])
    
    driver.quit()

debug_bdme()
