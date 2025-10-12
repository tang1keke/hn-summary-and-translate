"""Tests for RSS generator module."""

import pytest
from datetime import datetime
from lxml import etree
from src.generator import RSSGenerator, MultiLanguageRSSGenerator, generate_index_page
from pathlib import Path
import tempfile


class TestRSSGenerator:
    """Test cases for RSSGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create RSSGenerator instance."""
        return RSSGenerator("https://example.com", "en")

    @pytest.fixture
    def sample_items(self):
        """Create sample feed items."""
        return [
            {
                'title': 'Test Article 1',
                'link': 'https://example.com/article1',
                'description': 'This is a test description for article 1.',
                'published': datetime(2024, 1, 1, 12, 0, 0),
                'guid': 'guid-1',
                'author': 'Author 1',
                'score': 100,
                'comments': 'https://news.ycombinator.com/item?id=1'
            },
            {
                'title': 'Test Article 2',
                'link': 'https://example.com/article2',
                'description': 'This is a test description for article 2.',
                'published': datetime(2024, 1, 2, 12, 0, 0),
                'guid': 'guid-2',
                'tags': ['technology', 'programming']
            }
        ]

    def test_generate_feed(self, generator, sample_items):
        """Test RSS feed generation."""
        xml_content = generator.generate_feed(
            items=sample_items,
            title="Test Feed",
            description="Test feed description",
            feed_url="https://example.com/feed.xml"
        )

        # Parse XML to validate structure
        root = etree.fromstring(xml_content.encode('utf-8'))

        # Check RSS structure
        assert root.tag == 'rss'
        assert root.get('version') == '2.0'

        # Check channel metadata
        channel = root.find('channel')
        assert channel is not None
        assert channel.find('title').text == "Test Feed"
        assert channel.find('description').text == "Test feed description"
        assert channel.find('link').text == "https://example.com"
        assert channel.find('language').text == "en"

        # Check items
        items = channel.findall('item')
        assert len(items) == 2

        # Check first item details
        item1 = items[0]
        assert item1.find('title').text == "Test Article 1"
        assert item1.find('link').text == "https://example.com/article1"
        assert item1.find('guid').text == "guid-1"
        assert item1.find('comments').text == "https://news.ycombinator.com/item?id=1"

    def test_clean_text(self, generator):
        """Test text cleaning for XML."""
        dirty_text = "Text with control\x00characters\x01and\x1Fspecial chars"
        clean = generator._clean_text(dirty_text)

        # Control characters should be removed
        assert '\x00' not in clean
        assert '\x01' not in clean
        assert '\x1F' not in clean
        assert "Text with control" in clean

    def test_format_date(self, generator):
        """Test RSS date formatting."""
        dt = datetime(2024, 1, 15, 14, 30, 0)
        formatted = generator._format_date(dt)

        # Should be RFC 822 format
        assert "Mon, 15 Jan 2024" in formatted
        assert "14:30:00" in formatted

    def test_save_feed(self, generator):
        """Test saving feed to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.xml"
            xml_content = '<?xml version="1.0"?><rss><channel></channel></rss>'

            generator.save_feed(xml_content, str(output_path))

            assert output_path.exists()
            assert output_path.read_text() == xml_content


class TestMultiLanguageRSSGenerator:
    """Test cases for MultiLanguageRSSGenerator class."""

    @pytest.fixture
    def languages(self):
        """Language configuration."""
        return [
            {'code': 'en', 'name': 'English', 'feed_name': 'feed-en.xml'},
            {'code': 'ko', 'name': 'Korean', 'feed_name': 'feed-ko.xml'}
        ]

    @pytest.fixture
    def multi_generator(self, languages):
        """Create MultiLanguageRSSGenerator instance."""
        return MultiLanguageRSSGenerator("https://example.com", languages)

    def test_generate_all_feeds(self, multi_generator, languages):
        """Test generating feeds for all languages."""
        items_by_language = {
            'en': [
                {
                    'title': 'English Title',
                    'description': 'English description',
                    'link': 'https://example.com/1',
                    'guid': 'guid-1',
                    'published': datetime.now()
                }
            ],
            'ko': [
                {
                    'title': '한국어 제목',
                    'description': '한국어 설명',
                    'link': 'https://example.com/1',
                    'guid': 'guid-1',
                    'published': datetime.now()
                }
            ]
        }

        feeds = multi_generator.generate_all_feeds(items_by_language)

        assert len(feeds) == 2
        assert 'en' in feeds
        assert 'ko' in feeds

        # Validate XML for each feed
        for lang_code, xml_content in feeds.items():
            root = etree.fromstring(xml_content.encode('utf-8'))
            assert root.tag == 'rss'

    def test_save_all_feeds(self, multi_generator, languages):
        """Test saving all feeds to files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feeds = {
                'en': '<?xml version="1.0"?><rss><channel><title>EN</title></channel></rss>',
                'ko': '<?xml version="1.0"?><rss><channel><title>KO</title></channel></rss>'
            }

            multi_generator.save_all_feeds(feeds, tmpdir)

            # Check files were created
            output_path = Path(tmpdir)
            assert (output_path / 'feed-en.xml').exists()
            assert (output_path / 'feed-ko.xml').exists()


class TestGenerateIndexPage:
    """Test cases for generate_index_page function."""

    def test_generate_index_page(self):
        """Test index page generation."""
        languages = [
            {'code': 'en', 'name': 'English', 'feed_name': 'feed-en.xml'},
            {'code': 'ko', 'name': 'Korean', 'feed_name': 'feed-ko.xml'}
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_index_page("https://example.com", languages, tmpdir)

            index_path = Path(tmpdir) / 'index.html'
            assert index_path.exists()

            content = index_path.read_text()
            assert "HN RSS Translator" in content
            assert "English" in content
            assert "Korean" in content
            assert "feed-en.xml" in content
            assert "feed-ko.xml" in content