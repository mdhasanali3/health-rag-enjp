import logging
from typing import List, Literal, Optional
from functools import lru_cache
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global cache for translation models
_translation_pipelines = {}


def _get_transformer_pipeline(source_lang: str, target_lang: str):
    """Lazy load translation pipeline to avoid loading at startup"""
    from transformers import pipeline

    key = f"{source_lang}-{target_lang}"
    if key not in _translation_pipelines:
        if source_lang == "en" and target_lang == "ja":
            model_name = settings.translation_model_en_ja
        elif source_lang == "ja" and target_lang == "en":
            model_name = settings.translation_model_ja_en
        else:
            raise ValueError(f"Unsupported translation pair: {source_lang} -> {target_lang}")

        logger.info(f"Loading translation model: {model_name}")
        try:
            _translation_pipelines[key] = pipeline(
                "translation",
                model=model_name,
                device=-1  # CPU
            )
        except Exception as e:
            logger.error(f"Failed to load translation model {model_name}: {e}")
            raise

    return _translation_pipelines[key]


def translate(
    text: str,
    source_lang: Literal["en", "ja"],
    target_lang: Literal["en", "ja"]
) -> str:
    """
    Translate text between English and Japanese.

    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code

    Returns:
        Translated text, or original if translation fails or langs match
    """
    if not text or source_lang == target_lang:
        return text

    if settings.translation_backend == "none":
        logger.warning("Translation disabled in config")
        return text

    try:
        pipeline = _get_transformer_pipeline(source_lang, target_lang)
        result = pipeline(text, max_length=512)
        translated = result[0]["translation_text"]
        return translated
    except Exception as e:
        logger.error(f"Translation failed ({source_lang}->{target_lang}): {e}")
        # Return original text on failure
        return text


def translate_batch(
    texts: List[str],
    source_lang: Literal["en", "ja"],
    target_lang: Literal["en", "ja"]
) -> List[str]:
    """
    Batch translate multiple texts.

    Args:
        texts: List of texts to translate
        source_lang: Source language
        target_lang: Target language

    Returns:
        List of translated texts
    """
    if source_lang == target_lang:
        return texts

    translated = []
    for text in texts:
        translated.append(translate(text, source_lang, target_lang))

    return translated
