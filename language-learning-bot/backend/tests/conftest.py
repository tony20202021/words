"""
Pytest configuration and shared fixtures for backend tests.
"""

import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

def make_language(
    id: str = "507f1f77bcf86cd799439011",
    name_ru: str = "Китайский",
    name_foreign: str = "中文",
):
    from app.api.models.language import LanguageInDB
    return LanguageInDB(
        id=id,
        name_ru=name_ru,
        name_foreign=name_foreign,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


def make_word(
    id: str = "507f1f77bcf86cd799439022",
    language_id: str = "507f1f77bcf86cd799439011",
    word_foreign: str = "学习",
    translation: str = "учёба",
    word_number: int = 1,
):
    from app.api.models.word import WordInDB
    return WordInDB(
        id=id,
        language_id=language_id,
        word_foreign=word_foreign,
        translation=translation,
        transcription=None,
        word_number=word_number,
        radicals=None,
        references=None,
        tones=None,
        sounds=None,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


def make_user(
    id: str = "507f1f77bcf86cd799439033",
    telegram_id: int = 123456789,
    username: str = "testuser",
):
    from app.api.models.user import UserInDB
    return UserInDB(
        id=id,
        telegram_id=telegram_id,
        username=username,
        first_name="Test",
        last_name="User",
        is_admin=False,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


# ---------------------------------------------------------------------------
# Repository mocks
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_language_repo():
    repo = AsyncMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_name_ru = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=make_language())
    repo.update = AsyncMock(return_value=make_language())
    repo.delete = AsyncMock(return_value=True)
    repo.get_languages_with_word_count = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_word_repo():
    repo = AsyncMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_language_id = AsyncMock(return_value=[])
    repo.get_word_with_language_info = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=make_word())
    repo.update = AsyncMock(return_value=make_word())
    repo.delete = AsyncMock(return_value=True)
    repo.count_by_language_id = AsyncMock(return_value=0)
    repo.get_by_filter = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_telegram_id = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=make_user())
    repo.update = AsyncMock(return_value=make_user())
    repo.delete = AsyncMock(return_value=True)
    repo.count = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_statistics_repo():
    repo = AsyncMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_user_id = AsyncMock(return_value=[])
    repo.create = AsyncMock(return_value=MagicMock())
    repo.update = AsyncMock(return_value=MagicMock())
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.languages = MagicMock()
    db.words = MagicMock()
    db.users = MagicMock()
    db.statistics = MagicMock()
    return db


# ---------------------------------------------------------------------------
# FastAPI app + TestClient with overridden dependencies
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    with patch.dict(os.environ, {
        "MONGODB_URL": "mongodb://localhost:8527",
        "MONGODB_DB_NAME": "test_db",
    }), patch("app.db.database.hydra_available", False), \
       patch("app.db.database.db", MagicMock()), \
       patch("app.db.database.client", MagicMock()):
        from app.main_backend import create_application
        return create_application()


@pytest.fixture
def client(app, mock_language_repo, mock_user_repo, mock_word_repo, mock_statistics_repo):
    from app.core.dependencies import (
        get_language_service,
        get_user_service,
        get_word_service,
        get_statistics_service,
    )
    from app.services.language_service import LanguageService
    from app.services.user_service import UserService
    from app.services.word_service import WordService
    from app.services.statistics_service import StatisticsService

    app.dependency_overrides[get_language_service] = lambda: LanguageService(
        mock_language_repo, mock_word_repo, mock_statistics_repo
    )
    app.dependency_overrides[get_user_service] = lambda: UserService(mock_user_repo)
    app.dependency_overrides[get_word_service] = lambda: WordService(
        mock_word_repo, mock_language_repo
    )
    app.dependency_overrides[get_statistics_service] = lambda: StatisticsService(
        mock_statistics_repo, mock_word_repo
    )

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
