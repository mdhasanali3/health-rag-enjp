import logging
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect if text is English or Japanese.

    Args:
        text: Input text to analyze

    Returns:
        'en' or 'ja', defaults to 'en' if uncertain
    """
    if not text or len(text.strip()) < 3:
        return 'en'

    try:
        lang = detect(text)
        # Map detected language to our supported set
        if lang == 'ja':
            return 'ja'
        # Default everything else to English
        return 'en'
    except LangDetectException as e:
        logger.warning(f"Language detection failed: {e}. Defaulting to 'en'")
        return 'en'


def is_japanese(text: str) -> bool:
    """Quick check if text contains Japanese characters"""
    if not text:
        return False
    # Check for hiragana, katakana, or kanji
    for char in text:
        if '\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FFF':
            return True
    return False
