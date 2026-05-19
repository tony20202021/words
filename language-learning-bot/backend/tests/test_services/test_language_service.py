"""
Tests for LanguageService.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.language_service import LanguageService
from app.api.models.language import LanguageCreate, LanguageUpdate
from tests.conftest import make_language


@pytest.fixture
def service(mock_language_repo, mock_word_repo, mock_statistics_repo):
    return LanguageService(mock_language_repo, mock_word_repo, mock_statistics_repo)


class TestGetLanguages:
    @pytest.mark.asyncio
    async def test_get_languages_empty(self, service, mock_language_repo):
        mock_language_repo.get_all.return_value = []
        result = await service.get_languages()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_languages_returns_all(self, service, mock_language_repo):
        langs = [make_language(id="111"), make_language(id="222", name_ru="Японский")]
        mock_language_repo.get_all.return_value = langs
        result = await service.get_languages()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_languages_calls_repo(self, service, mock_language_repo):
        mock_language_repo.get_all.return_value = []
        await service.get_languages()
        mock_language_repo.get_all.assert_called_once()


class TestGetLanguage:
    @pytest.mark.asyncio
    async def test_get_existing_language(self, service, mock_language_repo):
        lang = make_language()
        mock_language_repo.get_by_id.return_value = lang
        result = await service.get_language(lang.id)
        assert result is not None
        assert result.id == lang.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_language_returns_none(self, service, mock_language_repo):
        mock_language_repo.get_by_id.return_value = None
        result = await service.get_language("000000000000000000000000")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_language_calls_repo_with_id(self, service, mock_language_repo):
        mock_language_repo.get_by_id.return_value = None
        await service.get_language("abc123")
        mock_language_repo.get_by_id.assert_called_once_with("abc123")


class TestCreateLanguage:
    @pytest.mark.asyncio
    async def test_create_language_success(self, service, mock_language_repo):
        lang_data = LanguageCreate(name_ru="Английский", name_foreign="English")
        created = make_language(name_ru="Английский", name_foreign="English")
        mock_language_repo.get_by_name_ru.return_value = None
        mock_language_repo.create.return_value = created
        result = await service.create_language(lang_data)
        assert result.name_ru == "Английский"

    @pytest.mark.asyncio
    async def test_create_duplicate_language_raises(self, service, mock_language_repo):
        existing = make_language()
        lang_data = LanguageCreate(name_ru=existing.name_ru, name_foreign=existing.name_foreign)
        mock_language_repo.get_by_name_ru.return_value = existing
        with pytest.raises(ValueError):
            await service.create_language(lang_data)

    @pytest.mark.asyncio
    async def test_create_calls_repo(self, service, mock_language_repo):
        lang_data = LanguageCreate(name_ru="Французский", name_foreign="Français")
        mock_language_repo.get_by_name_ru.return_value = None
        mock_language_repo.create.return_value = make_language(name_ru="Французский")
        await service.create_language(lang_data)
        mock_language_repo.create.assert_called_once()


class TestUpdateLanguage:
    @pytest.mark.asyncio
    async def test_update_existing_language(self, service, mock_language_repo):
        lang = make_language()
        updated = make_language(name_ru="Обновлённый")
        mock_language_repo.get_by_id.return_value = lang
        mock_language_repo.update.return_value = updated
        result = await service.update_language(lang.id, LanguageUpdate(name_ru="Обновлённый"))
        assert result.name_ru == "Обновлённый"

    @pytest.mark.asyncio
    async def test_update_nonexistent_language_returns_none(self, service, mock_language_repo):
        mock_language_repo.get_by_id.return_value = None
        result = await service.update_language("000", LanguageUpdate(name_ru="X"))
        assert result is None


class TestDeleteLanguage:
    @pytest.mark.asyncio
    async def test_delete_existing_language(self, service, mock_language_repo):
        lang = make_language()
        mock_language_repo.get_by_id.return_value = lang
        mock_language_repo.delete.return_value = True
        result = await service.delete_language(lang.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_language_returns_false(self, service, mock_language_repo):
        mock_language_repo.get_by_id.return_value = None
        result = await service.delete_language("000")
        assert result is False
