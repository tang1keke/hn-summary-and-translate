"""RSS feed generator module."""

import logging
import os
from datetime import datetime
from typing import List, Dict, Optional
from lxml import etree
from pathlib import Path
import html

logger = logging.getLogger(__name__)


class RSSGenerator:
    """Generates RSS 2.0 compliant XML feeds."""

    def __init__(self, base_url: str, language: str = 'en'):
        """
        Initialize RSS generator.

        Args:
            base_url: Base URL for the RSS feed
            language: Language code for the feed
        """
        self.base_url = base_url.rstrip('/')
        self.language = language

    def generate_feed(self,
                     items: List[Dict],
                     title: str = None,
                     description: str = None,
                     feed_url: str = None) -> str:
        """
        Generate RSS 2.0 XML feed.

        Args:
            items: List of feed items
            title: Feed title
            description: Feed description
            feed_url: Full URL of this feed

        Returns:
            RSS XML as string
        """
        # Create root RSS element
        rss = etree.Element('rss',
                           version='2.0',
                           nsmap={
                               'atom': 'http://www.w3.org/2005/Atom',
                               'dc': 'http://purl.org/dc/elements/1.1/'
                           })

        channel = etree.SubElement(rss, 'channel')

        # Add channel metadata
        self._add_channel_metadata(channel, title, description, feed_url)

        # Add items
        for item in items:
            self._add_item(channel, item)

        # Generate XML string
        xml_str = etree.tostring(
            rss,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        ).decode('utf-8')

        return xml_str

    def _add_channel_metadata(self,
                             channel: etree.Element,
                             title: str,
                             description: str,
                             feed_url: str):
        """Add channel metadata to RSS feed."""
        # Required channel elements
        etree.SubElement(channel, 'title').text = title or f'Hacker News - {self.language.upper()}'
        etree.SubElement(channel, 'link').text = self.base_url
        etree.SubElement(channel, 'description').text = description or f'Hacker News feed translated to {self.language}'

        # Optional channel elements
        etree.SubElement(channel, 'language').text = self.language
        etree.SubElement(channel, 'lastBuildDate').text = self._format_date(datetime.now())
        etree.SubElement(channel, 'generator').text = 'HN RSS Translator'

        # Add atom:link for feed autodiscovery
        if feed_url:
            atom_link = etree.SubElement(
                channel,
                '{http://www.w3.org/2005/Atom}link',
                rel='self',
                type='application/rss+xml',
                href=feed_url
            )

    def _add_item(self, channel: etree.Element, item: Dict):
        """Add an item to the RSS channel."""
        item_elem = etree.SubElement(channel, 'item')

        # Required item elements
        title = item.get('title', 'No title')
        etree.SubElement(item_elem, 'title').text = self._clean_text(title)

        link = item.get('link', '')
        if link:
            etree.SubElement(item_elem, 'link').text = link

        # Description (summary)
        description = item.get('description', '')
        if description:
            # Include both translated and original content
            full_description = self._format_description(item)
            etree.SubElement(item_elem, 'description').text = full_description

        # GUID (globally unique identifier)
        guid = item.get('guid', link)
        if guid:
            guid_elem = etree.SubElement(item_elem, 'guid')
            guid_elem.text = guid
            guid_elem.set('isPermaLink', 'false' if not guid.startswith('http') else 'true')

        # Publication date
        published = item.get('published')
        if published:
            if isinstance(published, datetime):
                pub_date = self._format_date(published)
            else:
                pub_date = published
            etree.SubElement(item_elem, 'pubDate').text = pub_date

        # Comments link (HN specific)
        comments = item.get('comments')
        if comments:
            etree.SubElement(item_elem, 'comments').text = comments

        # Author
        author = item.get('author')
        if author:
            etree.SubElement(item_elem, '{http://purl.org/dc/elements/1.1/}creator').text = author

        # Categories/tags
        tags = item.get('tags', [])
        for tag in tags:
            etree.SubElement(item_elem, 'category').text = tag

    def _format_description(self, item: Dict) -> str:
        """
        Format item description with translated and original content.

        Args:
            item: Item dictionary

        Returns:
            Formatted description
        """
        description_parts = []

        # Add translated summary
        summary = item.get('description', '')
        if summary:
            description_parts.append(f"📝 {summary}")

        # Add original title if different
        original_title = item.get('original_title')
        if original_title and original_title != item.get('title'):
            description_parts.append(f"\n\n🔤 Original: {original_title}")

        # Add metadata if available
        score = item.get('score')
        if score:
            description_parts.append(f"\n📊 Score: {score} points")

        # Add source link
        link = item.get('link')
        if link:
            description_parts.append(f"\n🔗 Read more: {link}")

        return '\n'.join(description_parts)

    def _clean_text(self, text: str) -> str:
        """Clean and escape text for XML."""
        if not text:
            return ''

        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')

        # The lxml library handles XML escaping automatically
        return text.strip()

    def _format_date(self, dt: datetime) -> str:
        """Format datetime for RSS (RFC 822)."""
        # RSS requires RFC 822 date format
        return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')

    def save_feed(self, xml_content: str, output_path: str):
        """
        Save RSS feed to file.

        Args:
            xml_content: RSS XML content
            output_path: Path to save the file
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(xml_content, encoding='utf-8')
            logger.info(f"RSS feed saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save RSS feed: {e}")
            raise


class MultiLanguageRSSGenerator:
    """Generates RSS feeds for multiple languages."""

    def __init__(self, base_url: str, languages: List[Dict]):
        """
        Initialize multi-language RSS generator.

        Args:
            base_url: Base URL for feeds
            languages: List of language configurations
        """
        self.base_url = base_url
        self.languages = languages
        self.generators = {}

        for lang_config in languages:
            lang_code = lang_config['code']
            self.generators[lang_code] = RSSGenerator(base_url, lang_code)

    def generate_all_feeds(self, items_by_language: Dict[str, List[Dict]]) -> Dict[str, str]:
        """
        Generate RSS feeds for all languages.

        Args:
            items_by_language: Dictionary mapping language codes to items

        Returns:
            Dictionary mapping language codes to RSS XML
        """
        feeds = {}

        for lang_config in self.languages:
            lang_code = lang_config['code']
            lang_name = lang_config['name']

            items = items_by_language.get(lang_code, [])
            if not items:
                logger.warning(f"No items for language {lang_code}")
                continue

            generator = self.generators[lang_code]
            feed_url = f"{self.base_url}/{lang_config['feed_name']}"

            xml_content = generator.generate_feed(
                items=items,
                title=f"Hacker News - {lang_name}",
                description=f"Hacker News articles summarized and translated to {lang_name}",
                feed_url=feed_url
            )

            feeds[lang_code] = xml_content
            logger.info(f"Generated RSS feed for {lang_name} with {len(items)} items")

        return feeds

    def save_all_feeds(self, feeds: Dict[str, str], output_dir: str):
        """
        Save all RSS feeds to files.

        Args:
            feeds: Dictionary mapping language codes to RSS XML
            output_dir: Directory to save feeds
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for lang_config in self.languages:
            lang_code = lang_config['code']
            feed_name = lang_config['feed_name']

            if lang_code in feeds:
                file_path = output_path / feed_name
                file_path.write_text(feeds[lang_code], encoding='utf-8')
                logger.info(f"Saved {feed_name}")


def generate_index_page(base_url: str, languages: List[Dict], output_dir: str):
    """
    Generate an index HTML page listing all available feeds.

    Args:
        base_url: Base URL for feeds
        languages: List of language configurations
        output_dir: Directory to save index page
    """
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HN RSS Translator - Available Feeds</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1 {{
            color: #ff6600;
        }}
        .feed-list {{
            list-style: none;
            padding: 0;
        }}
        .feed-item {{
            margin: 15px 0;
            padding: 15px;
            background: #f6f6f6;
            border-radius: 8px;
        }}
        .feed-link {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }}
        .feed-link:hover {{
            text-decoration: underline;
        }}
        .feed-url {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
            word-break: break-all;
        }}
        .updated {{
            color: #666;
            font-size: 0.9em;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>🗞️ HN RSS Translator</h1>
    <p>Hacker News articles automatically summarized and translated into multiple languages.</p>

    <h2>Available Feeds</h2>
    <ul class="feed-list">
"""

    for lang_config in languages:
        lang_name = lang_config['name']
        feed_name = lang_config['feed_name']
        feed_url = f"{base_url}/{feed_name}"

        html_content += f"""
        <li class="feed-item">
            <a href="{feed_name}" class="feed-link">📡 {lang_name}</a>
            <div class="feed-url">{feed_url}</div>
        </li>
"""

    html_content += f"""
    </ul>

    <p class="updated">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>

    <hr>
    <p style="text-align: center; color: #666; font-size: 0.9em;">
        <a href="https://github.com/hevinxx/hn-summary-and-translate">GitHub</a> |
        Powered by BART summarization and Google Translate
    </p>
</body>
</html>
"""

    output_path = Path(output_dir) / 'index.html'
    output_path.write_text(html_content, encoding='utf-8')
    logger.info(f"Generated index page at {output_path}")


def test_generator():
    """Test RSS generator with sample data."""
    # Sample items
    items = [
        {
            'title': 'Test Article 1',
            'link': 'https://example.com/1',
            'description': 'This is a test summary of article 1.',
            'published': datetime.now(),
            'guid': 'test-1',
            'author': 'Test Author',
            'score': 42
        },
        {
            'title': 'Test Article 2',
            'link': 'https://example.com/2',
            'description': 'This is a test summary of article 2.',
            'published': datetime.now(),
            'guid': 'test-2',
            'comments': 'https://news.ycombinator.com/item?id=123'
        }
    ]

    # Generate single feed
    generator = RSSGenerator('https://example.com', 'en')
    xml_content = generator.generate_feed(items)

    print("Generated RSS feed:")
    print(xml_content[:500] + "...")

    # Validate XML
    try:
        etree.fromstring(xml_content.encode('utf-8'))
        print("\n✅ XML is valid")
    except Exception as e:
        print(f"\n❌ XML validation failed: {e}")