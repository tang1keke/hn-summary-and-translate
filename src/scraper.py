"""Web scraper module for extracting article content."""

import requests
import logging
import time
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class WebScraper:
    """Scrapes and extracts main content from web pages."""

    DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; HN-RSS-Translator/1.0; +https://github.com/hevinxx/hn-summary-and-translate)"
    DEFAULT_TIMEOUT = 10
    MAX_CONTENT_LENGTH = 5000
    MAX_RETRIES = 2

    def __init__(self, user_agent: str = None, timeout: int = None):
        """
        Initialize web scraper.

        Args:
            user_agent: Custom user agent string
            timeout: Request timeout in seconds
        """
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a session with proper headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session

    def extract_content(self, url: str) -> Optional[str]:
        """
        Extract main content from a web page.

        Args:
            url: URL of the page to scrape

        Returns:
            Extracted text content or None if failed
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(f"Scraping {url} (attempt {attempt + 1})")

                # Make request
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract content based on site structure
                content = self._extract_article_content(soup, url)

                if content:
                    logger.debug(f"Successfully extracted {len(content)} characters from {url}")
                    return content[:self.MAX_CONTENT_LENGTH]
                else:
                    logger.warning(f"No content extracted from {url}")
                    return None

            except requests.RequestException as e:
                logger.warning(f"Request error for {url}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return None

            except Exception as e:
                logger.error(f"Unexpected error scraping {url}: {e}")
                return None

    def _extract_article_content(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """
        Extract article content using various strategies.

        Args:
            soup: BeautifulSoup parsed HTML
            url: Original URL (for site-specific extraction)

        Returns:
            Extracted text content
        """
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Try different extraction strategies
        content = None

        # Strategy 1: Look for article/main tags
        article = soup.find('article') or soup.find('main')
        if article:
            content = self._clean_text(article.get_text())
            if len(content) > 200:
                return content

        # Strategy 2: Look for common content containers
        content_selectors = [
            'div[class*="content"]',
            'div[class*="article"]',
            'div[class*="post"]',
            'div[class*="entry"]',
            'div[class*="text"]',
            'div[role="main"]',
            'section[class*="content"]'
        ]

        for selector in content_selectors:
            container = soup.select_one(selector)
            if container:
                content = self._clean_text(container.get_text())
                if len(content) > 200:
                    return content

        # Strategy 3: Get paragraphs with substantial text
        paragraphs = soup.find_all('p')
        if len(paragraphs) >= 3:
            text_blocks = []
            for p in paragraphs:
                text = self._clean_text(p.get_text())
                if len(text) > 50:  # Filter out short paragraphs
                    text_blocks.append(text)

            if text_blocks:
                content = ' '.join(text_blocks)
                if len(content) > 200:
                    return content

        # Strategy 4: Site-specific extraction
        domain = urlparse(url).netloc
        if 'github.com' in domain:
            return self._extract_github_content(soup)
        elif 'medium.com' in domain or 'towardsdatascience.com' in domain:
            return self._extract_medium_content(soup)
        elif 'arxiv.org' in domain:
            return self._extract_arxiv_content(soup)

        # Fallback: Get all text
        content = self._clean_text(soup.get_text())
        return content if len(content) > 200 else None

    def _extract_github_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from GitHub pages."""
        # For README files
        readme = soup.select_one('article[class*="markdown-body"]')
        if readme:
            return self._clean_text(readme.get_text())

        # For code files
        code_view = soup.select_one('div[class*="blob-wrapper"]')
        if code_view:
            return self._clean_text(code_view.get_text())

        return None

    def _extract_medium_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from Medium articles."""
        article_body = soup.select_one('article section')
        if article_body:
            return self._clean_text(article_body.get_text())
        return None

    def _extract_arxiv_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from arXiv papers."""
        abstract = soup.select_one('blockquote[class*="abstract"]')
        if abstract:
            return self._clean_text(abstract.get_text())
        return None

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Remove common artifacts
        text = text.replace('\xa0', ' ')  # Non-breaking spaces
        text = text.replace('\u200b', '')  # Zero-width spaces

        return text.strip()


def batch_scrape(urls: List[str],
                 max_workers: int = 5,
                 user_agent: str = None,
                 timeout: int = None) -> Dict[str, Optional[str]]:
    """
    Scrape multiple URLs concurrently.

    Args:
        urls: List of URLs to scrape
        max_workers: Maximum number of concurrent workers
        user_agent: Custom user agent
        timeout: Request timeout

    Returns:
        Dictionary mapping URLs to their extracted content
    """
    scraper = WebScraper(user_agent=user_agent, timeout=timeout)
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(scraper.extract_content, url): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                content = future.result()
                results[url] = content
                if content:
                    logger.info(f"✓ Scraped {url[:50]}... ({len(content)} chars)")
                else:
                    logger.warning(f"✗ Failed to scrape {url[:50]}...")
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                results[url] = None

    return results


def test_scraper(url: str = "https://example.com"):
    """Test scraper with a sample URL."""
    scraper = WebScraper()
    content = scraper.extract_content(url)
    if content:
        print(f"Successfully extracted {len(content)} characters")
        print(f"Preview: {content[:200]}...")
    else:
        print("Failed to extract content")
    return content