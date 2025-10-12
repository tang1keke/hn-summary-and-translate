# HN RSS Translator 🌐

Automatically summarize and translate Hacker News RSS feeds into multiple languages using AI, running completely free on GitHub Actions.

## Features ✨

- 📡 **Automatic RSS Processing**: Fetches HN RSS feed every 3 hours
- 🌐 **Web Content Extraction**: Scrapes actual article content, not just RSS descriptions
- 🤖 **AI Summarization**: Uses Facebook's BART model for intelligent summarization
- 🌍 **Multi-Language Translation**: Supports 100+ languages via Google Translate
- 💰 **Completely Free**: Runs on GitHub Actions and GitHub Pages
- 🚀 **Serverless**: No server required, fully automated
- ⚡ **Cached & Optimized**: Smart caching to avoid reprocessing

## Quick Start 🚀

### 1. Fork this Repository

Click the "Fork" button at the top right of this page.

### 2. Enable GitHub Actions

Go to Settings → Actions → General and enable "Allow all actions and reusable workflows"

### 3. Configure Your Languages

Edit `config.yaml` to set your desired languages:

```yaml
translation:
  target_languages:
    - code: "ko"
      name: "Korean"
      feed_name: "rss-ko.xml"
    - code: "ja"
      name: "Japanese"
      feed_name: "rss-ja.xml"
```

### 4. Enable GitHub Pages

1. Go to Settings → Pages
2. Set Source to "Deploy from a branch"
3. Choose branch: `gh-pages` (will be created automatically)

### 5. Trigger First Run

Go to Actions tab → "Update RSS Feeds" → "Run workflow"

### 6. Subscribe to Your Feed

After the first run completes, your feeds will be available at:
```
https://YOUR_USERNAME.github.io/hn-summary-and-translate/rss-ko.xml
```

## Configuration 🔧

### config.yaml

```yaml
general:
  source_feed: "https://news.ycombinator.com/rss"
  update_frequency: "0 */3 * * *"  # Every 3 hours

summarization:
  model: "facebook/bart-large-cnn"  # Or "sshleifer/distilbart-cnn-12-6" for speed
  max_length: 150
  min_length: 50

translation:
  provider: "google"  # Options: google, libre, mymemory
  target_languages:
    - code: "ko"
      name: "Korean"
      feed_name: "rss-ko.xml"

filtering:
  max_items: 30  # Limit for GitHub Actions runtime
  max_age_hours: 24
  skip_jobs: false  # Filter out job postings

output:
  base_url: "https://USERNAME.github.io/hn-summary-and-translate"
  keep_days: 7
  generate_index: true
```

## Architecture 🏗️

```
HN RSS Feed → Fetch → Scrape Articles → Summarize (BART) → Translate → Generate RSS → Deploy to GitHub Pages
```

### Components

- **Fetcher**: Retrieves and filters RSS feed items
- **Scraper**: Extracts full article content from web pages
- **Summarizer**: Uses BART model for intelligent summarization
- **Translator**: Multi-language translation with fallback providers
- **Generator**: Creates RSS 2.0 compliant XML feeds
- **Cache Manager**: Prevents reprocessing with intelligent caching

## Local Development 💻

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/hn-summary-and-translate
cd hn-summary-and-translate

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Locally

```bash
# Full run
python main.py

# Test mode (3 items only)
python main.py --test

# Debug mode
python main.py --log-level DEBUG
```

### Run Tests

```bash
pytest tests/ -v
```

## GitHub Actions Details ⚙️

The workflow runs automatically every 3 hours and:

1. **Caches Models**: ~1.6GB BART model cached between runs
2. **Processes Efficiently**: Completes in 10-20 minutes
3. **Handles Errors**: Continues even if individual items fail
4. **Deploys Automatically**: Updates GitHub Pages with new feeds

### Resource Usage

- **GitHub Actions**: ~480 minutes/month (well under 2000 free minutes)
- **Storage**: ~2GB for model cache
- **Runtime**: 10-20 minutes per run

## Troubleshooting 🔍

### Common Issues

**No feeds generated**
- Check Actions tab for error logs
- Ensure GitHub Pages is enabled
- Verify config.yaml syntax

**Translation fails**
- API might be rate limited, wait and retry
- Try switching provider in config.yaml

**Summarization too slow**
- Switch to DistilBART model for faster processing
- Reduce max_items in config.yaml

**GitHub Actions timeout**
- Reduce max_items to 20 or less
- Use lighter summarization model

## Advanced Features 🎯

### Custom Summarization Models

```yaml
summarization:
  model: "sshleifer/distilbart-cnn-12-6"  # Faster, lighter
  # model: "facebook/bart-large-cnn"  # Better quality
```

### Multiple Translation Providers

```yaml
translation:
  provider: "mymemory"  # Alternative to Google
  # provider: "libre"  # Open source option
```

### Filtering Options

```yaml
filtering:
  skip_jobs: true  # Skip job postings
  max_age_hours: 12  # Only recent items
```

## Contributing 🤝

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License 📄

MIT License - See [LICENSE](LICENSE) file

## Credits 🙏

- **BART Model**: Facebook AI Research
- **Translation**: Google Translate via deep-translator
- **Infrastructure**: GitHub Actions & GitHub Pages

---

Made with ❤️ for the Hacker News community

**Note**: This project is not affiliated with Y Combinator or Hacker News.