from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from webdriver_manager.chrome import ChromeDriverManager


def initialize_driver(): 
    chrome_options = webdriver.ChromeOptions()
    download_path = r'/Users/btp712/Code/Anki crawler/audio/'
    prefs={"profile.managed_default_content_settings.images": 2, 'disk-cache-size': 4096,
           "download.default_directory": download_path}
    chrome_options.add_experimental_option("prefs", prefs) # Manage image loading and run on disk cache
    # chrome_options.add_argument("--headless") # Runs Chrome in headless mode
    chrome_options.add_argument('--no-sandbox') # Bypass OS security model
    chrome_options.add_argument('--disable-dev-shm-usage') # overcome limited resource problems
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

    return driver