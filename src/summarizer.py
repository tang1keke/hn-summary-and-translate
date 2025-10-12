"""Text summarization module using Hugging Face transformers."""

import logging
import torch
from typing import List, Optional, Dict
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import os

logger = logging.getLogger(__name__)


class Summarizer:
    """Text summarizer using BART or other transformer models."""

    DEFAULT_MODEL = "facebook/bart-large-cnn"
    FALLBACK_MODEL = "sshleifer/distilbart-cnn-12-6"  # Smaller alternative

    def __init__(self,
                 model_name: str = None,
                 max_length: int = 150,
                 min_length: int = 50,
                 use_gpu: bool = False):
        """
        Initialize summarizer with specified model.

        Args:
            model_name: Name of the model to use
            max_length: Maximum length of summary
            min_length: Minimum length of summary
            use_gpu: Whether to use GPU if available
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.max_length = max_length
        self.min_length = min_length
        self.device = 0 if use_gpu and torch.cuda.is_available() else -1

        self.summarizer = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the summarization model with error handling."""
        try:
            logger.info(f"Loading summarization model: {self.model_name}")

            # Set cache directory if specified
            cache_dir = os.environ.get('HF_HOME', None)

            # Try to load the model
            self.summarizer = pipeline(
                "summarization",
                model=self.model_name,
                device=self.device,
                cache_dir=cache_dir
            )

            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")

            # Try fallback model if main model fails
            if self.model_name != self.FALLBACK_MODEL:
                logger.info(f"Attempting to load fallback model: {self.FALLBACK_MODEL}")
                self.model_name = self.FALLBACK_MODEL
                try:
                    self.summarizer = pipeline(
                        "summarization",
                        model=self.model_name,
                        device=self.device
                    )
                    logger.info("Fallback model loaded successfully")
                except Exception as e2:
                    logger.error(f"Failed to load fallback model: {e2}")
                    raise RuntimeError("Could not load any summarization model")
            else:
                raise

    def summarize(self, text: str, custom_max_length: int = None) -> str:
        """
        Generate summary of the given text.

        Args:
            text: Text to summarize
            custom_max_length: Override default max length for this summary

        Returns:
            Summarized text
        """
        if not text or len(text.strip()) < 50:
            logger.debug("Text too short to summarize")
            return text

        # Truncate very long texts to avoid token limits
        max_input_length = 1024
        if len(text) > max_input_length * 4:  # Rough character to token ratio
            logger.debug(f"Truncating input from {len(text)} to ~{max_input_length * 4} chars")
            text = text[:max_input_length * 4]

        try:
            max_len = custom_max_length or self.max_length

            # Ensure min_length is not greater than max_length
            min_len = min(self.min_length, max_len - 10)

            result = self.summarizer(
                text,
                max_length=max_len,
                min_length=min_len,
                do_sample=False,
                truncation=True
            )

            summary = result[0]['summary_text']
            logger.debug(f"Generated summary of {len(summary)} chars from {len(text)} chars")
            return summary

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            # Return truncated original text as fallback
            return text[:self.max_length] + "..." if len(text) > self.max_length else text

    def batch_summarize(self, texts: List[str], batch_size: int = 4) -> List[str]:
        """
        Summarize multiple texts in batches.

        Args:
            texts: List of texts to summarize
            batch_size: Number of texts to process at once

        Returns:
            List of summaries
        """
        summaries = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                # Process batch
                batch_results = self.summarizer(
                    batch,
                    max_length=self.max_length,
                    min_length=self.min_length,
                    do_sample=False,
                    truncation=True
                )

                for result in batch_results:
                    summaries.append(result['summary_text'])

            except Exception as e:
                logger.error(f"Batch summarization failed: {e}")
                # Fallback to individual processing
                for text in batch:
                    summaries.append(self.summarize(text))

        return summaries

    def get_model_info(self) -> Dict:
        """Get information about the loaded model."""
        return {
            'model_name': self.model_name,
            'max_length': self.max_length,
            'min_length': self.min_length,
            'device': 'GPU' if self.device >= 0 else 'CPU'
        }


class LightweightSummarizer:
    """Lightweight text summarizer using extractive methods (no model required)."""

    def __init__(self, max_sentences: int = 3):
        """
        Initialize lightweight summarizer.

        Args:
            max_sentences: Maximum number of sentences in summary
        """
        self.max_sentences = max_sentences

    def summarize(self, text: str) -> str:
        """
        Extract key sentences from text as summary.

        Args:
            text: Text to summarize

        Returns:
            Extracted summary
        """
        import re

        if not text:
            return ""

        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if len(sentences) <= self.max_sentences:
            return '. '.join(sentences) + '.'

        # Simple scoring based on word frequency
        word_freq = {}
        for sentence in sentences:
            words = sentence.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_freq[word] = word_freq.get(word, 0) + 1

        # Score sentences
        sentence_scores = {}
        for sentence in sentences:
            words = sentence.lower().split()
            score = sum(word_freq.get(word, 0) for word in words if len(word) > 3)
            sentence_scores[sentence] = score / max(len(words), 1)

        # Get top sentences
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)
        selected = [s[0] for s in top_sentences[:self.max_sentences]]

        # Maintain original order
        summary = []
        for sentence in sentences:
            if sentence in selected:
                summary.append(sentence)
                if len(summary) >= self.max_sentences:
                    break

        return '. '.join(summary) + '.'


def test_summarizer(text: str = None):
    """Test summarizer with sample text."""
    if not text:
        text = """
        Artificial intelligence has made remarkable progress in recent years.
        Machine learning models can now understand and generate human-like text,
        translate between languages, and even write code. These advancements have
        led to new applications in healthcare, education, and business. However,
        there are still challenges to overcome, including bias in training data
        and the need for more efficient algorithms. Researchers continue to work
        on these problems while exploring new frontiers in AI capabilities.
        """

    # Test transformer-based summarizer
    try:
        summarizer = Summarizer()
        summary = summarizer.summarize(text)
        print("Transformer Summary:")
        print(summary)
        print()
    except Exception as e:
        print(f"Transformer summarizer failed: {e}")

    # Test lightweight summarizer
    light_summarizer = LightweightSummarizer()
    light_summary = light_summarizer.summarize(text)
    print("Lightweight Summary:")
    print(light_summary)