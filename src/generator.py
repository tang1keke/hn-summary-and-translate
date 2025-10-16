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

        # Generate XML string with stylesheet processing instruction
        xml_str = etree.tostring(
            rss,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        ).decode('utf-8')

        # Insert XSLT stylesheet processing instruction after XML declaration
        xml_lines = xml_str.split('\n')
        if xml_lines[0].startswith('<?xml'):
            xml_lines.insert(1, '<?xml-stylesheet type="text/xsl" href="rss-style.xsl"?>')
            xml_str = '\n'.join(xml_lines)

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
            etree.SubElement(item_elem, 'description').text = self._clean_text(full_description)

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
            etree.SubElement(item_elem, '{http://purl.org/dc/elements/1.1/}creator').text = self._clean_text(author)

        # Categories/tags
        tags = item.get('tags', [])
        for tag in tags:
            etree.SubElement(item_elem, 'category').text = self._clean_text(tag)

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

        # Copy XSLT stylesheet to output directory
        xsl_source = Path(__file__).parent / 'templates' / 'rss-style.xsl'
        xsl_dest = output_path / 'rss-style.xsl'
        if xsl_source.exists():
            xsl_dest.write_text(xsl_source.read_text(encoding='utf-8'), encoding='utf-8')
            logger.info("Copied XSLT stylesheet to output directory")

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
    # Generate language list for meta tags
    lang_names = ', '.join([lang['name'] for lang in languages])
    lang_names_short = ', '.join([lang['name'] for lang in languages[:3]])
    if len(languages) > 3:
        lang_names_short += f", and {len(languages) - 3} more"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Hacker News articles automatically summarized and translated into multiple languages ({lang_names}). Get multilingual tech news via RSS feeds.">
    <meta name="keywords" content="Hacker News, RSS, translation, {lang_names}, tech news, summarization, multilingual">
    <meta name="robots" content="index, follow">

    <!-- Open Graph / Social Media -->
    <meta property="og:title" content="HN RSS Translator - Multilingual Hacker News Feeds">
    <meta property="og:description" content="Get Hacker News in your language with automatic summarization and translation">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{base_url}/">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="HN RSS Translator">
    <meta name="twitter:description" content="Multilingual Hacker News RSS feeds with AI summarization">

    <title>HN RSS Translator - Multilingual Hacker News Feeds ({lang_names_short})</title>

    <!-- Schema.org Structured Data -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "HN RSS Translator",
      "description": "Hacker News articles automatically summarized and translated into multiple languages",
      "url": "{base_url}/",
      "potentialAction": {{
        "@type": "SearchAction",
        "target": "{base_url}/?q={{search_term_string}}",
        "query-input": "required name=search_term_string"
      }}
    }}
    </script>

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
        .feed-url-container {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 5px;
        }}
        .feed-url {{
            color: #666;
            font-size: 0.9em;
            word-break: break-all;
            flex: 1;
        }}
        .copy-btn {{
            padding: 6px 12px;
            background: #ff6600;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
            white-space: nowrap;
            transition: background 0.2s;
        }}
        .copy-btn:hover {{
            background: #ff8533;
        }}
        .copy-btn:active {{
            background: #cc5200;
        }}
        .copy-btn.copied {{
            background: #28a745;
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
            <div class="feed-url-container">
                <code class="feed-url">{feed_url}</code>
                <button class="copy-btn" onclick="copyToClipboard('{feed_url}', this)">📋 Copy</button>
            </div>
        </li>
"""

    html_content += f"""
    </ul>

    <section style="margin-top: 30px; line-height: 1.8; background: white; padding: 20px; border-radius: 8px;">
        <h2 style="color: #ff6600;">Why Use HN RSS Translator?</h2>
        <ul style="margin-left: 20px;">
            <li><strong>Automatic Translation</strong>: Get Hacker News articles in {lang_names_short}</li>
            <li><strong>AI Summarization</strong>: BART model provides concise summaries of long articles</li>
            <li><strong>Fresh Content</strong>: Updated every 3 hours with latest tech news</li>
            <li><strong>Free & Open Source</strong>: No API keys required, runs on GitHub infrastructure</li>
        </ul>

        <h3 style="color: #ff6600; margin-top: 20px;">Supported Languages</h3>
        <p>We currently support feeds in: <strong>{lang_names}</strong>.</p>

        <h3 style="color: #ff6600; margin-top: 20px;">How to Use</h3>
        <p>Simply copy one of the RSS feed URLs above and add it to your favorite RSS reader such as Feedly, Inoreader, NetNewsWire, or any other RSS client.</p>
    </section>

    <p class="updated">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>

    <hr>
    <p style="text-align: center; color: #666; font-size: 0.9em;">
        <a href="https://github.com/hevinxx/hn-summary-and-translate">GitHub</a> |
        Powered by BART summarization and Google Translate
    </p>

    <script>
        function copyToClipboard(text, button) {{
            navigator.clipboard.writeText(text).then(() => {{
                const originalText = button.textContent;
                button.textContent = '✅ Copied!';
                button.classList.add('copied');

                setTimeout(() => {{
                    button.textContent = originalText;
                    button.classList.remove('copied');
                }}, 2000);
            }}).catch(err => {{
                console.error('Failed to copy:', err);
                alert('Failed to copy to clipboard');
            }});
        }}
    </script>
</body>
</html>
"""

    output_path = Path(output_dir) / 'index.html'
    output_path.write_text(html_content, encoding='utf-8')
    logger.info(f"Generated index page at {output_path}")


def generate_sitemap(base_url: str, languages: List[Dict], output_dir: str):
    """
    Generate sitemap.xml for SEO.

    Args:
        base_url: Base URL for the site
        languages: List of language configurations
        output_dir: Directory to save sitemap
    """
    today = datetime.now().strftime('%Y-%m-%d')

    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
"""

    for lang_config in languages:
        feed_name = lang_config['feed_name']
        sitemap_content += f"""  <url>
    <loc>{base_url}/{feed_name}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
"""

    sitemap_content += "</urlset>\n"

    output_path = Path(output_dir) / 'sitemap.xml'
    output_path.write_text(sitemap_content, encoding='utf-8')
    logger.info(f"Generated sitemap at {output_path}")


def generate_robots_txt(base_url: str, output_dir: str):
    """
    Generate robots.txt for search engine crawlers.

    Args:
        base_url: Base URL for the site
        output_dir: Directory to save robots.txt
    """
    robots_content = f"""User-agent: *
Allow: /
Sitemap: {base_url}/sitemap.xml

# Exclude cache directory
Disallow: /cache/
"""

    output_path = Path(output_dir) / 'robots.txt'
    output_path.write_text(robots_content, encoding='utf-8')
    logger.info(f"Generated robots.txt at {output_path}")


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