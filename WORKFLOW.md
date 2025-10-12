# HN RSS Translator - Implementation Workflow

## Executive Summary
Serverless RSS feed translator using GitHub Actions, BART summarization, and Google Translate. Zero-cost operation with 10-20 minute processing cycles.

## Phase 1: Core MVP Implementation

### Week 1: Project Foundation & Parallel Development

#### Track A: Infrastructure Setup (Day 1-2)
```bash
# 1.1 Initialize Project Structure
mkdir -p src tests cache output templates .github/workflows
touch src/{__init__,fetcher,scraper,summarizer,translator,generator,utils}.py
touch main.py config.yaml requirements.txt .env.example

# 1.2 Core Dependencies
cat > requirements.txt << 'EOF'
feedparser==6.0.10
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
deep-translator==1.11.4
transformers==4.35.2
torch==2.1.0
python-dotenv==1.0.0
pyyaml==6.0.1
pytest==7.4.3
pytest-mock==3.12.0
EOF

# 1.3 Configuration Template
cat > config.yaml << 'EOF'
general:
  source_feed: "https://news.ycombinator.com/rss"
  update_frequency: "0 */3 * * *"
  timezone: "UTC"

summarization:
  model: "facebook/bart-large-cnn"
  max_length: 150
  min_length: 50

translation:
  provider: "google"
  target_languages:
    - code: "ko"
      name: "Korean"
      feed_name: "rss-ko.xml"

filtering:
  max_items: 30
  max_age_hours: 24
  skip_jobs: false

output:
  base_url: "https://username.github.io/hn-rss-translator"
  keep_days: 7
EOF
```

**Validation**: ✓ All files created, ✓ Dependencies installable

#### Track B: Core Components (Day 2-5) - PARALLEL DEVELOPMENT

##### B1: RSS Fetcher Module
```python
# src/fetcher.py
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict

def fetch_feed(url: str, max_age_hours: int = 24) -> List[Dict]:
    """Fetch and filter RSS feed items."""
    feed = feedparser.parse(url)
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

    items = []
    for entry in feed.entries:
        published = datetime(*entry.published_parsed[:6])
        if published > cutoff_time:
            items.append({
                'title': entry.title,
                'link': entry.link,
                'description': entry.get('description', ''),
                'published': published,
                'guid': entry.get('id', entry.link),
                'comments': entry.get('comments', '')
            })
    return items
```

**Test**: `pytest tests/test_fetcher.py -v`

##### B2: Web Scraper Module
```python
# src/scraper.py
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def extract_content(url: str, timeout: int = 10) -> str:
    """Extract main content from webpage."""
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; HN-RSS-Translator/1.0)'}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract text
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text[:5000]  # Limit for summarization
    except Exception as e:
        return None

def batch_scrape(urls: List[str], max_workers: int = 5) -> Dict[str, str]:
    """Scrape multiple URLs concurrently."""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(extract_content, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            results[url] = future.result()
    return results
```

**Test**: `python -c "from src.scraper import extract_content; print(extract_content('https://example.com')[:100])"`

##### B3: Summarizer Module
```python
# src/summarizer.py
from transformers import pipeline
import torch

class Summarizer:
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        """Initialize with model caching support."""
        self.summarizer = pipeline(
            "summarization",
            model=model_name,
            device=-1  # CPU only for GitHub Actions
        )

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate summary of text."""
        if not text or len(text) < 50:
            return text

        try:
            result = self.summarizer(
                text,
                max_length=max_length,
                min_length=50,
                do_sample=False
            )
            return result[0]['summary_text']
        except Exception:
            return text[:max_length]
```

**Validation**: Model downloads successfully, summarization works

##### B4: Translator Module
```python
# src/translator.py
from deep_translator import GoogleTranslator
from typing import Dict, List

class MultiTranslator:
    def __init__(self, target_languages: List[str]):
        """Initialize translators for each language."""
        self.translators = {
            lang: GoogleTranslator(source='en', target=lang)
            for lang in target_languages
        }

    def translate_text(self, text: str, target_lang: str) -> str:
        """Translate text to target language."""
        try:
            return self.translators[target_lang].translate(text)
        except Exception:
            return text  # Fallback to original

    def translate_item(self, item: Dict, languages: List[str]) -> Dict:
        """Translate item into multiple languages."""
        translations = {}
        for lang in languages:
            translations[lang] = {
                'title': self.translate_text(item['title'], lang),
                'description': self.translate_text(item['description'], lang)
            }
        return translations
```

**Test**: Verify translation for sample text

##### B5: RSS Generator Module
```python
# src/generator.py
from lxml import etree
from datetime import datetime
import os

def generate_rss(items: List[Dict], lang_code: str, base_url: str) -> str:
    """Generate RSS 2.0 XML."""
    rss = etree.Element('rss', version='2.0')
    channel = etree.SubElement(rss, 'channel')

    # Channel metadata
    etree.SubElement(channel, 'title').text = f'Hacker News - {lang_code.upper()}'
    etree.SubElement(channel, 'link').text = base_url
    etree.SubElement(channel, 'description').text = f'HN translated to {lang_code}'
    etree.SubElement(channel, 'language').text = lang_code
    etree.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Add items
    for item in items:
        item_elem = etree.SubElement(channel, 'item')
        etree.SubElement(item_elem, 'title').text = item['title']
        etree.SubElement(item_elem, 'link').text = item['link']
        etree.SubElement(item_elem, 'description').text = item['description']
        etree.SubElement(item_elem, 'guid').text = item['guid']
        etree.SubElement(item_elem, 'pubDate').text = item['published'].strftime('%a, %d %b %Y %H:%M:%S +0000')

    return etree.tostring(rss, pretty_print=True, xml_declaration=True, encoding='UTF-8').decode('utf-8')
```

### Week 2: Integration & Automation

#### Day 6-7: Main Orchestrator
```python
# main.py
import yaml
import json
import os
from pathlib import Path
from src.fetcher import fetch_feed
from src.scraper import batch_scrape
from src.summarizer import Summarizer
from src.translator import MultiTranslator
from src.generator import generate_rss
from src.utils import load_cache, save_cache, deduplicate_items

def main():
    # Load configuration
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize components
    summarizer = Summarizer(config['summarization']['model'])
    languages = [lang['code'] for lang in config['translation']['target_languages']]
    translator = MultiTranslator(languages)

    # Fetch RSS feed
    print("📡 Fetching RSS feed...")
    items = fetch_feed(
        config['general']['source_feed'],
        config['filtering']['max_age_hours']
    )[:config['filtering']['max_items']]

    # Load cache and deduplicate
    cache = load_cache()
    new_items = deduplicate_items(items, cache)
    print(f"📊 Processing {len(new_items)} new items")

    # Scrape content
    print("🔍 Extracting web content...")
    urls = [item['link'] for item in new_items]
    content_map = batch_scrape(urls)

    # Process items
    processed_items = []
    for item in new_items:
        content = content_map.get(item['link'], item['description'])

        # Summarize
        if content:
            item['summary'] = summarizer.summarize(content)
        else:
            item['summary'] = item['description']

        # Translate
        item['translations'] = translator.translate_item(
            {'title': item['title'], 'description': item['summary']},
            languages
        )

        processed_items.append(item)
        cache[item['guid']] = item

    # Generate RSS feeds
    print("📝 Generating RSS feeds...")
    os.makedirs('output', exist_ok=True)

    for lang_config in config['translation']['target_languages']:
        lang_code = lang_config['code']
        feed_items = []

        for item in processed_items:
            if lang_code in item['translations']:
                feed_items.append({
                    'title': item['translations'][lang_code]['title'],
                    'description': item['translations'][lang_code]['description'],
                    'link': item['link'],
                    'guid': item['guid'],
                    'published': item['published']
                })

        rss_content = generate_rss(feed_items, lang_code, config['output']['base_url'])
        output_path = Path('output') / lang_config['feed_name']
        output_path.write_text(rss_content)

    # Save cache
    save_cache(cache)
    print("✅ RSS feeds generated successfully!")

if __name__ == "__main__":
    main()
```

#### Day 8-9: GitHub Actions Workflow
```yaml
# .github/workflows/update-rss.yml
name: Update RSS Feeds

on:
  schedule:
    - cron: '0 */3 * * *'  # Every 3 hours
  workflow_dispatch:  # Manual trigger

jobs:
  update-feeds:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
    - name: Checkout repository
      uses: actions/checkout@v3
      with:
        persist-credentials: false
        fetch-depth: 0

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
        cache: 'pip'

    - name: Cache Hugging Face models
      uses: actions/cache@v3
      with:
        path: ~/.cache/huggingface
        key: ${{ runner.os }}-huggingface-bart-${{ hashFiles('requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-huggingface-bart-

    - name: Install dependencies
      run: |
        pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run RSS translator
      run: |
        python main.py
      env:
        TRANSFORMERS_CACHE: ~/.cache/huggingface
        HF_HOME: ~/.cache/huggingface

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./output
        keep_files: false
```

#### Day 10: Testing & Validation

##### Unit Tests
```python
# tests/test_integration.py
import pytest
from unittest.mock import Mock, patch

def test_end_to_end_flow():
    """Test complete pipeline with mocked external services."""
    with patch('src.fetcher.feedparser.parse') as mock_parse:
        mock_parse.return_value = Mock(entries=[...])

        with patch('src.scraper.requests.get') as mock_get:
            mock_get.return_value = Mock(content=b'<html>Test content</html>')

            # Run main pipeline
            # Assert outputs exist
            assert Path('output/rss-ko.xml').exists()
```

##### Integration Test Script
```bash
#!/bin/bash
# test_integration.sh
echo "🧪 Running integration tests..."

# Test with small RSS feed
python -c "
from src.fetcher import fetch_feed
items = fetch_feed('https://news.ycombinator.com/rss')
assert len(items) > 0
print(f'✓ Fetched {len(items)} items')
"

# Test model loading
python -c "
from src.summarizer import Summarizer
s = Summarizer()
result = s.summarize('This is a long text that needs to be summarized.')
assert len(result) > 0
print('✓ Summarizer works')
"

# Test translation
python -c "
from src.translator import MultiTranslator
t = MultiTranslator(['ko'])
result = t.translate_text('Hello world', 'ko')
assert result != 'Hello world'
print('✓ Translation works')
"

echo "✅ All tests passed!"
```

### Validation Checkpoints

| Component | Success Criteria | Test Command |
|-----------|-----------------|--------------|
| RSS Fetcher | Fetches 30 items < 1s | `pytest tests/test_fetcher.py` |
| Web Scraper | Extracts content from 80% URLs | `python -m src.scraper --test` |
| Summarizer | Model loads, generates summaries | `python -c "from src.summarizer import Summarizer; print('OK')"` |
| Translator | Translates to all target languages | `pytest tests/test_translator.py` |
| RSS Generator | Valid XML output | `xmllint --noout output/rss-*.xml` |
| GitHub Action | Completes in <30 min | Check Actions tab |
| GitHub Pages | RSS accessible via URL | `curl https://username.github.io/hn-rss-translator/rss-ko.xml` |

## Phase 2: Stabilization (Week 3)

### Enhanced Error Handling
```python
# src/utils.py additions
import json
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

class ResilientProcessor:
    def __init__(self, max_retries=3, cache_dir='cache'):
        self.max_retries = max_retries
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic."""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff

class CacheManager:
    def __init__(self, cache_file='cache/processed_items.json', ttl_days=7):
        self.cache_file = Path(cache_file)
        self.ttl_days = ttl_days
        self.cache_file.parent.mkdir(exist_ok=True)

    def load(self):
        """Load cache with TTL enforcement."""
        if not self.cache_file.exists():
            return {}

        with open(self.cache_file) as f:
            cache = json.load(f)

        # Clean old entries
        cutoff = (datetime.now() - timedelta(days=self.ttl_days)).isoformat()
        cache = {k: v for k, v in cache.items()
                if v.get('processed_at', '') > cutoff}

        return cache

    def save(self, cache):
        """Save cache with timestamp."""
        for key in cache:
            if 'processed_at' not in cache[key]:
                cache[key]['processed_at'] = datetime.now().isoformat()

        with open(self.cache_file, 'w') as f:
            json.dump(cache, f, indent=2, default=str)

def deduplicate_by_url(items, cache):
    """Remove duplicate items by URL hash."""
    seen = set(cache.keys())
    unique_items = []

    for item in items:
        url_hash = hashlib.md5(item['link'].encode()).hexdigest()
        if url_hash not in seen:
            unique_items.append(item)
            seen.add(url_hash)

    return unique_items
```

### Improved Logging
```python
# src/logger.py
import logging
from datetime import datetime

def setup_logger(name='hn-rss-translator'):
    """Configure structured logging."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

logger = setup_logger()

# Usage in main.py
logger.info(f"Processing batch: {len(items)} items")
logger.warning(f"Failed to scrape: {url}")
logger.error(f"Translation failed: {e}")
```

## Phase 3: Optimization (Week 4)

### Performance Optimizations
```python
# Batch processing for translations
def batch_translate(items, translator, batch_size=10):
    """Process translations in batches."""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        # Process batch
        results.extend(batch)
    return results

# Memory-efficient processing
def process_items_generator(items):
    """Process items as generator to reduce memory."""
    for item in items:
        yield process_single_item(item)

# Parallel summarization
from concurrent.futures import ThreadPoolExecutor

def parallel_summarize(texts, summarizer, max_workers=3):
    """Summarize multiple texts in parallel."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(summarizer.summarize, text) for text in texts]
        return [f.result() for f in futures]
```

### Model Optimization Options
```yaml
# config.yaml - lightweight option
summarization:
  model: "sshleifer/distilbart-cnn-12-6"  # Smaller, faster
  # model: "facebook/bart-large-cnn"  # Original, better quality
```

## Testing & Deployment Strategy

### CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
name: CI Tests

on:
  pull_request:
  push:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - run: pip install -r requirements.txt
    - run: pytest tests/ -v --cov=src
    - run: python -m pylint src/
```

### Staged Rollout
1. **Development Branch**: All changes first
2. **Test Workflow**: Run with test RSS feed (5 items)
3. **Staging**: Deploy to staging GitHub Pages
4. **Production**: Merge to main after validation

### Monitoring & Alerts
```python
# monitoring.py
def check_feed_health(feed_url):
    """Validate RSS feed is accessible and valid."""
    try:
        response = requests.get(feed_url)
        etree.fromstring(response.content)
        return True
    except:
        # Send alert (webhook, email, etc.)
        return False
```

## Risk Mitigation

| Risk | Mitigation | Fallback |
|------|------------|----------|
| GitHub Actions timeout | Limit to 30 items, add progress logging | Reduce batch size |
| Model download fails | Cache aggressively, retry logic | Use lighter model |
| Translation API limits | Rate limiting, provider rotation | Keep English version |
| Web scraping blocked | User-agent rotation, respect robots.txt | Use RSS description |
| Memory overflow | Process in batches, use generators | Reduce concurrent operations |

## Success Metrics

- ✅ **MVP Launch**: All Phase 1 tasks complete
- ✅ **Performance**: <20 min execution time
- ✅ **Reliability**: 95% successful runs
- ✅ **Quality**: Valid RSS output, readable translations
- ✅ **Cost**: $0 operational cost achieved

## Next Steps After MVP

1. **Phase 4**: Web interface with statistics
2. **Phase 5**: Multiple RSS sources support
3. **Community**: Documentation, contribution guide
4. **Scale**: Docker option for self-hosting