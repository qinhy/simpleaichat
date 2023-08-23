from models import CommonMessage, CommonChatSession, Function
from utils import wikipedia_search, wikipedia_search_lookup
from pathlib import Path
from sys import platform
from typing import TYPE_CHECKING, Optional, Type

from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeDriverService
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.options import ArgOptions as BrowserOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeDriverService
from selenium.webdriver.edge.webdriver import WebDriver as EdgeDriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as GeckoDriverService
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.safari.webdriver import WebDriver as SafariDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager as EdgeDriverManager

class WikipediaSearch(Function):
    description: str = 'search information from wiki and get topics'
    _parameters_description = dict(
        query='the key words use for searching'
    )
    def __call__(self, query: str):
        wiki_matches = wikipedia_search(query, n=3)
        if len(wiki_matches)==0:
            wiki_matches = ['nothing found!']
        return {"titles": wiki_matches, "context": ", ".join(wiki_matches), }
    
    def __init__(self, *args,**kwargs):
        super(self.__class__, self).__init__(*args,**kwargs)
        self._extract_signature()

class WikipediaLookup(Function):
    description: str = 'lookup more information about a topic.'
    _parameters_description = dict(
        query='the key words use for lookup'
    )
    def __call__(self, query: str):
        page = wikipedia_search_lookup(query, sentences=3)
        return page
    
    def __init__(self, *args,**kwargs):
        super(self.__class__, self).__init__(*args,**kwargs)
        self._extract_signature()

class BrowseLink(Function):
    description: str = 'browse the information from the link.'
    _parameters_description = dict(
        link='URL link to browse.'
    )
    def __call__(self, link: str):
        page,_ = self.browse_website(link)
        return page
    
    def __init__(self, *args,**kwargs):
        super(self.__class__, self).__init__(*args,**kwargs)
        self._extract_signature()

    def _parse_qiita(self, html_doc :str):
        soup = BeautifulSoup(html_doc, 'html.parser')
        # Extract title
        # title = soup.title.text
        # Extract all paragraphs 
        paragraphs = soup.find_all('p')
        # Extract toc
        toc = soup.find('div', class_='p-items_toc')
        # Extract article body
        article_body = soup.find('div', id='personal-public-article-body')
        # Extract author name
        author_name = soup.find('a', href='/yulily')
        # Extract tags
        tags = soup.find_all('a', class_='style-okdcjo')
        # Extract number of likes
        likes = soup.find('a', class_='style-1vpukh3')
        # Extract number of stocks  
        stocks = soup.find('span', class_='style-1grh9bf')
        return article_body
    

    def browse_website(self, url: str) -> str:
        driver = None
        text,links = 'can not open the link!','can not open the link!'
        try:
            driver = self.open_page_in_browser(url)
            page_source = driver.execute_script("return document.body.outerHTML;")

            page = self.scrape_text_with_selenium(url, page_source)
            text = page.text
            links = ''#scrape_links_with_selenium(driver, url)
            
        except Exception as e:
            print(e)
        finally:
            if driver:
                driver.quit()
            
            return text,links

    def scrape_text_with_selenium(self, link :str, page_source: str) -> str:
        """Scrape text from a browser window using selenium

        Args:
            driver (WebDriver): A driver object representing the browser window to scrape

        Returns:
            str: the text scraped from the website
        """

        # Get the HTML content directly from the browser's DOM
        # page_source = driver.execute_script("return document.body.outerHTML;")
        if 'https://qiita.com' in link:
            return self._parse_qiita(page_source)
        
        soup = BeautifulSoup(page_source, "html.parser")

        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        return text


    def scrape_links_with_selenium(self, driver: WebDriver, base_url: str) -> list[str]:
        pass


    def open_page_in_browser(self, url: str, selenium_web_browser:str='chrome', selenium_headless:bool=True) -> WebDriver:
        """Open a browser window and load a web page using Selenium

        Params:
            url (str): The URL of the page to load
            config (Config): The applicable application configuration

        Returns:
            driver (WebDriver): A driver object representing the browser window to scrape
        """

        options_available: dict[str, Type[BrowserOptions]] = {
            "chrome": ChromeOptions,
            "edge": EdgeOptions,
            "firefox": FirefoxOptions,
            "safari": SafariOptions,
        }

        options: BrowserOptions = options_available[selenium_web_browser]()
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.49 Safari/537.36"
        )

        if selenium_web_browser == "firefox":
            if selenium_headless:
                options.headless = True
                options.add_argument("--disable-gpu")
            driver = FirefoxDriver(
                service=GeckoDriverService(GeckoDriverManager().install()), options=options
            )
        elif selenium_web_browser == "edge":
            driver = EdgeDriver(
                service=EdgeDriverService(EdgeDriverManager().install()), options=options
            )
        elif selenium_web_browser == "safari":
            # Requires a bit more setup on the users end
            # See https://developer.apple.com/documentation/webkit/testing_with_webdriver_in_safari
            driver = SafariDriver(options=options)
        else:
            if platform == "linux" or platform == "linux2":
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--remote-debugging-port=9222")

            options.add_argument("--no-sandbox")
            if selenium_headless:
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")

            chromium_driver_path = Path("/usr/bin/chromedriver")

            driver = ChromeDriver(
                service=ChromeDriverService(str(chromium_driver_path))
                if chromium_driver_path.exists()
                else ChromeDriverService(ChromeDriverManager().install()),
                options=options,
            )
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        return driver
