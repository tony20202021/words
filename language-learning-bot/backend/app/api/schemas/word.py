"""
Схемы ответов по словам для роутов языков.

Почему список полей здесь не повторяется
----------------------------------------
Раньше этот файл держал собственную копию всех полей слова, и копий стало две:
`app.api.models.word` — та, что используется восемью модулями приложения, и эта,
которую импортирует ровно один роут. Копии разошлись молча. В 3.0.81 новые поля
`part_of_speech` и `lemma` добавили именно сюда — в ту, что почти никем не
читается, — и правка просто не сработала: API продолжал отдавать None, а
причину было не видно, потому что файл выглядел правильным.

Теперь список полей ровно один — в `models.word.WordBase`. Здесь остаётся только
то, чем ответ роута отличается от общей модели: у него необязательные отметки
времени, потому что не всякая проекция их выбирает.
"""

from typing import Optional
from datetime import datetime
from pydantic import Field

from app.api.models.word import WordBase, WordCreate, WordUpdate  # noqa: F401


class WordResponse(WordBase):
    """Схема ответа по слову."""
    id: str = Field(..., description="Word ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class WordWithLanguageResponse(WordResponse):
    """Схема ответа по слову вместе с языком."""
    language_name_ru: str = Field(..., description="Russian name of the language")
    language_name_foreign: str = Field(..., description="Native name of the language")
