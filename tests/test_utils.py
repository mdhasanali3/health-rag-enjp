import pytest
from app.utils.langdetect import detect_language, is_japanese
from app.utils.translation import translate


def test_detect_language_english():
    """Test English text detection"""
    text = "This is a test sentence in English."
    assert detect_language(text) == "en"


def test_detect_language_japanese():
    """Test Japanese text detection"""
    text = "これは日本語のテストです。"
    assert detect_language(text) == "ja"


def test_detect_language_empty():
    """Test empty text defaults to English"""
    assert detect_language("") == "en"
    assert detect_language("   ") == "en"


def test_is_japanese():
    """Test Japanese character detection"""
    assert is_japanese("これはテスト") == True
    assert is_japanese("This is English") == False
    assert is_japanese("Mixed text 日本語") == True


def test_translate_same_language():
    """Test translation with same source/target returns original"""
    text = "Test text"
    result = translate(text, "en", "en")
    assert result == text


def test_translate_empty():
    """Test translation of empty text"""
    result = translate("", "en", "ja")
    assert result == ""
