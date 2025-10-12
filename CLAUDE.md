# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**HN RSS Translator** - An open-source serverless tool that automatically summarizes and translates Hacker News RSS feeds using free AI libraries and GitHub infrastructure.

## Core Architecture

### System Design
This is a **serverless application** designed to run entirely on GitHub Actions and GitHub Pages:
- **Execution**: GitHub Actions runs every 3 hours via cron schedule
- **Processing**: Fetches HN RSS → Crawls linked pages → Summarizes content → Translates → Generates new RSS
- **Hosting**: Generated RSS feeds are deployed to GitHub Pages
- **Caching**: Uses GitHub Actions cache for Hugging Face models (~1.6GB BART model)

### Key Technical Decisions
- **No API Keys Required**: Uses facebook/bart-large-cnn for summarization (runs locally) and Google Translate via deep-translator (free tier)
- **Web Content Extraction**: BeautifulSoup4 extracts actual article content from linked pages, not just RSS descriptions
- **Parallel Processing**: Implements concurrent web crawling (max 5 simultaneous) to optimize GitHub Actions runtime
- **Stateless Design**: Each run is independent; uses file-based caching for processed items

## Development Commands

### Local Development
```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run main process
python main.py

# Run tests
python -m pytest tests/ -v

# Run with custom config
python main.py --config custom-config.yaml
```

### GitHub Actions Testing
```bash
# Test workflow locally with act (optional)
act -j update-feeds

# Validate workflow syntax
yamllint .github/workflows/update-rss.yml
```

## Project Structure & Responsibilities

### Core Modules
- `src/fetcher.py`: RSS feed collection and parsing using feedparser
- `src/scraper.py`: Web content extraction with BeautifulSoup4, handles various site structures
- `src/summarizer.py`: BART model integration for content summarization
- `src/translator.py`: Multi-language translation via deep-translator
- `src/generator.py`: RSS 2.0 XML generation with proper encoding
- `src/utils.py`: Caching logic, URL deduplication, helper functions
- `main.py`: Orchestrates the entire pipeline with error recovery

### Configuration System
The `config.yaml` file controls all behavior:
- `general.update_frequency`: Cron expression for GitHub Actions schedule
- `summarization.max_length`: Summary length in tokens (default: 150)
- `translation.target_languages`: Array of language configurations
- `filtering.max_items`: Limits items to process (important for GitHub Actions time limits)
- `output.base_url`: GitHub Pages URL for absolute RSS links

### Performance Constraints
GitHub Actions limits that affect the design:
- **6-hour max runtime**: Current design targets 10-20 minutes per run
- **7GB RAM**: BART model uses ~2GB, leaves room for concurrent operations
- **2000 minutes/month free**: Running every 3 hours uses ~480 minutes/month

## Critical Implementation Notes

### Model Caching Strategy
The BART model (~1.6GB) MUST be cached to avoid re-downloading:
```python
# Always check for cached model first
model_path = Path.home() / ".cache" / "huggingface"
if not model_path.exists():
    # First-time download will happen
    pass
```

### Web Crawling Resilience
```python
# Essential patterns for reliable crawling
timeout = 10  # Seconds
max_retries = 2
user_agent = "Mozilla/5.0 (compatible; HN-RSS-Translator/1.0)"
# Must handle failures gracefully - skip items that fail to load
```

### RSS Generation Rules
- Always escape special characters in XML
- Include both original and translated content in description
- Maintain stable GUIDs for feed readers
- Use proper datetime formatting (RFC 822)

### Error Handling Philosophy
- **Never fail the entire run** due to single item failures
- Log errors but continue processing remaining items
- Provide fallbacks: failed translation → use original, failed crawl → use RSS description
- Cache successful results to avoid re-processing

## Common Tasks & Solutions

### Adding a New Language
1. Update `config.yaml` with new language code
2. Verify deep-translator supports it: `deep-translator --list`
3. Test locally first with small batch
4. Monitor first GitHub Actions run for timeout issues

### Debugging Crawling Issues
1. Check `src/scraper.py` extraction patterns
2. Test specific URL with: `python -c "from src.scraper import extract_content; print(extract_content('URL'))"`
3. Add site-specific extractors if needed
4. Consider adding to robots.txt compliance

### Optimizing Runtime
1. Reduce `filtering.max_items` if approaching 30-minute mark
2. Implement batch translation requests
3. Skip already-processed items via cache
4. Use lighter model (DistilBART) if needed

## GitHub Actions Workflow

The workflow in `.github/workflows/update-rss.yml` handles:
1. Python environment setup with dependency caching
2. Hugging Face model caching (critical for performance)
3. Main script execution with error capture
4. Automatic deployment to GitHub Pages

Key environment variables set by the workflow:
- `GITHUB_TOKEN`: Auto-provided for Pages deployment
- `HF_HOME`: Points to cached model directory

## Testing Strategy

### Unit Tests
- `tests/test_scraper.py`: Mock HTML responses for extraction testing
- `tests/test_summarizer.py`: Use small test model or mock
- `tests/test_translator.py`: Mock translation API responses
- `tests/test_generator.py`: Validate RSS XML structure

### Integration Tests
- Use small test RSS feed (3-5 items)
- Mock external services when possible
- Verify end-to-end pipeline with cached data

## Deployment Checklist

Before deploying or making significant changes:
1. ✓ Test locally with full RSS feed
2. ✓ Verify config.yaml syntax
3. ✓ Check GitHub Actions minutes remaining
4. ✓ Ensure Pages is enabled in repo settings
5. ✓ Validate output RSS with online validator
6. ✓ Test with actual RSS reader application