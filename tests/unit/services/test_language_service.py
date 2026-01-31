"""Unit tests for language service."""

import pytest
from pathlib import Path

from app.services.language_service import LanguageService
from app.storage.models import Language


class TestLanguageService:
    """Tests for LanguageService class."""

    @pytest.fixture
    def service(self) -> LanguageService:
        """Create a language service instance."""
        return LanguageService()

    def test_default_language(self, service: LanguageService):
        """Test default language is English."""
        assert service.default_language == Language.EN

    def test_supported_languages(self, service: LanguageService):
        """Test supported languages."""
        assert Language.EN in service.supported_languages
        assert Language.HU in service.supported_languages
        assert len(service.supported_languages) == 2

    def test_detect_language_english(self, service: LanguageService):
        """Test detecting English text."""
        text = "How do I install the framework? What are the requirements?"
        assert service.detect_language(text) == Language.EN

    def test_detect_language_hungarian(self, service: LanguageService):
        """Test detecting Hungarian text."""
        text = "Hogyan telepíthetem a keretrendszert? Mi a teendő?"
        assert service.detect_language(text) == Language.HU

    def test_detect_language_hungarian_simple(self, service: LanguageService):
        """Test detecting simple Hungarian text."""
        text = "Az én kérdésem az, hogy hogyan lehet ezt megoldani."
        assert service.detect_language(text) == Language.HU

    def test_detect_language_empty(self, service: LanguageService):
        """Test detecting empty text returns default."""
        assert service.detect_language("") == Language.EN
        assert service.detect_language("   ") == Language.EN

    def test_detect_language_code(self, service: LanguageService):
        """Test code-heavy text defaults to English."""
        text = "def foo(): return bar.baz()"
        assert service.detect_language(text) == Language.EN

    def test_set_user_preference(self, service: LanguageService):
        """Test setting user language preference."""
        service.set_user_preference("user@example.com", Language.HU)
        assert service.get_user_preference("user@example.com") == Language.HU

    def test_get_user_preference_default(self, service: LanguageService):
        """Test getting default preference for unknown user."""
        assert service.get_user_preference("unknown@example.com") == Language.EN

    def test_user_preference_case_insensitive(self, service: LanguageService):
        """Test user preference lookup is case insensitive."""
        service.set_user_preference("User@Example.COM", Language.HU)
        assert service.get_user_preference("user@example.com") == Language.HU

    def test_clear_user_preference(self, service: LanguageService):
        """Test clearing user preference."""
        service.set_user_preference("user@example.com", Language.HU)
        service.clear_user_preference("user@example.com")
        assert service.get_user_preference("user@example.com") == Language.EN

    def test_clear_user_preference_not_found(self, service: LanguageService):
        """Test clearing non-existent preference doesn't error."""
        service.clear_user_preference("unknown@example.com")  # Should not raise

    def test_parse_language_english(self, service: LanguageService):
        """Test parsing English language strings."""
        assert service.parse_language("en") == Language.EN
        assert service.parse_language("EN") == Language.EN
        assert service.parse_language("english") == Language.EN
        assert service.parse_language("English") == Language.EN
        assert service.parse_language("eng") == Language.EN

    def test_parse_language_hungarian(self, service: LanguageService):
        """Test parsing Hungarian language strings."""
        assert service.parse_language("hu") == Language.HU
        assert service.parse_language("HU") == Language.HU
        assert service.parse_language("hungarian") == Language.HU
        assert service.parse_language("Hungarian") == Language.HU
        assert service.parse_language("magyar") == Language.HU
        assert service.parse_language("hun") == Language.HU

    def test_parse_language_invalid(self, service: LanguageService):
        """Test parsing invalid language strings."""
        assert service.parse_language("invalid") is None
        assert service.parse_language("fr") is None
        assert service.parse_language("") is None

    def test_is_supported(self, service: LanguageService):
        """Test checking language support."""
        assert service.is_supported(Language.EN) is True
        assert service.is_supported(Language.HU) is True

    def test_get_language_name(self, service: LanguageService):
        """Test getting language display names."""
        assert service.get_language_name(Language.EN) == "English"
        assert service.get_language_name(Language.HU) == "Hungarian"

    def test_get_docs_path(self, service: LanguageService):
        """Test getting documentation paths."""
        en_path = service.get_docs_path(Language.EN)
        hu_path = service.get_docs_path(Language.HU)
        assert en_path.name == "en"
        assert hu_path.name == "hu"

    def test_get_qa_file_path(self, service: LanguageService):
        """Test getting Q&A file paths."""
        en_path = service.get_qa_file_path(Language.EN)
        hu_path = service.get_qa_file_path(Language.HU)
        assert en_path.name == "accepted_qa_en.md"
        assert hu_path.name == "accepted_qa_hu.md"

    def test_get_suggestions_file_path(self, service: LanguageService):
        """Test getting suggestions file path."""
        path = service.get_suggestions_file_path()
        assert path.name == "suggested_features.md"

    def test_get_drafts_file_path(self, service: LanguageService):
        """Test getting drafts file path."""
        path = service.get_drafts_file_path()
        assert path.name == "draft_updates.md"


class TestLanguageDetectionEdgeCases:
    """Edge case tests for language detection."""

    @pytest.fixture
    def service(self) -> LanguageService:
        """Create a language service instance."""
        return LanguageService()

    def test_mixed_language_english_dominant(self, service: LanguageService):
        """Test mixed text with English dominant."""
        text = "The installation process is simple and you can start immediately."
        assert service.detect_language(text) == Language.EN

    def test_mixed_language_hungarian_dominant(self, service: LanguageService):
        """Test mixed text with Hungarian dominant."""
        text = "Ez a dokumentáció segít neked, hogy megértsd a rendszert."
        assert service.detect_language(text) == Language.HU

    def test_single_word_english(self, service: LanguageService):
        """Test single English word."""
        assert service.detect_language("hello") == Language.EN

    def test_single_word_hungarian(self, service: LanguageService):
        """Test single Hungarian word."""
        assert service.detect_language("hogyan") == Language.HU

    def test_numbers_only(self, service: LanguageService):
        """Test numbers only defaults to English."""
        assert service.detect_language("12345") == Language.EN

    def test_special_characters(self, service: LanguageService):
        """Test special characters only defaults to English."""
        assert service.detect_language("!@#$%^&*()") == Language.EN

    def test_url_in_text(self, service: LanguageService):
        """Test text with URL."""
        text = "Please visit https://example.com for more information."
        assert service.detect_language(text) == Language.EN
