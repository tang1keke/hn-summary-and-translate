"""Tests for web scraper module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup
from src.scraper import WebScraper, batch_scrape


class TestWebScraper:
    """Test cases for WebScraper class."""

    @pytest.fixture
    def scraper(self):
        """Create WebScraper instance."""
        return WebScraper()

    @pytest.fixture
    def mock_html_content(self):
        """Create mock HTML content."""
        return """
        <html>
        <head><title>Test Article</title></head>
        <body>
            <article>
                <h1>Main Article Title</h1>
                <p>This is the first paragraph with important content.</p>
                <p>This is the second paragraph with more details about the topic.</p>
                <p>And here is a third paragraph to make the content substantial.</p>
            </article>
            <script>console.log('should be removed');</script>
            <style>body { color: black; }</style>
        </body>
        </html>
        """

    def test_extract_content_success(self, scraper, mock_html_content):
        """Test successful content extraction."""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.content = mock_html_content.encode()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            content = scraper.extract_content("https://example.com")

            assert content is not None
            assert "Main Article Title" in content
            assert "first paragraph" in content
            assert "console.log" not in content  # Script should be removed
            assert "color: black" not in content  # Style should be removed

    def test_extract_content_with_retry(self, scraper):
        """Test content extraction with retry on failure."""
        with patch.object(scraper.session, 'get') as mock_get:
            # First call fails, second succeeds
            mock_get.side_effect = [
                requests.RequestException("Network error"),
                Mock(content=b"<html><body><p>Content after retry</p></body></html>")
            ]

            with patch('time.sleep'):  # Speed up test
                content = scraper.extract_content("https://example.com")

            assert mock_get.call_count == 2
            assert content is not None

    def test_extract_content_all_retries_fail(self, scraper):
        """Test content extraction when all retries fail."""
        with patch.object(scraper.session, 'get') as mock_get:
            mock_get.side_effect = requests.RequestException("Persistent error")

            with patch('time.sleep'):  # Speed up test
                content = scraper.extract_content("https://example.com")

            assert content is None
            assert mock_get.call_count == scraper.MAX_RETRIES

    def test_extract_github_content(self, scraper):
        """Test GitHub-specific content extraction."""
        github_html = """
        <html>
        <body>
            <article class="markdown-body">
                <h1>README</h1>
                <p>This is a GitHub repository README file.</p>
                <p>It contains project documentation.</p>
            </article>
        </body>
        </html>
        """

        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.content = github_html.encode()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            content = scraper.extract_content("https://github.com/user/repo")

            assert "README" in content
            assert "project documentation" in content

    def test_clean_text(self, scraper):
        """Test text cleaning functionality."""
        dirty_text = """
        Text with    multiple   spaces

        And multiple


        newlines
        \xa0Non-breaking space
        \u200bZero-width space
        """

        clean = scraper._clean_text(dirty_text)

        assert "multiple spaces" in clean
        assert "\xa0" not in clean
        assert "\u200b" not in clean
        assert "  " not in clean  # No double spaces


class TestBatchScrape:
    """Test cases for batch_scrape function."""

    def test_batch_scrape_success(self):
        """Test batch scraping multiple URLs."""
        urls = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com"
        ]

        with patch('src.scraper.WebScraper') as MockScraper:
            mock_instance = MockScraper.return_value
            mock_instance.extract_content.side_effect = [
                "Content 1",
                "Content 2",
                None  # Third URL fails
            ]

            results = batch_scrape(urls, max_workers=2)

            assert len(results) == 3
            assert results[urls[0]] == "Content 1"
            assert results[urls[1]] == "Content 2"
            assert results[urls[2]] is None

    def test_batch_scrape_with_exception(self):
        """Test batch scraping with exception handling."""
        urls = ["https://example.com"]

        with patch('src.scraper.WebScraper') as MockScraper:
            mock_instance = MockScraper.return_value
            mock_instance.extract_content.side_effect = Exception("Unexpected error")

            with patch('src.scraper.logger'):
                results = batch_scrape(urls)

            # Should handle exception and return None
            assert results[urls[0]] is None