"""
Скрипт создания оптимальных индексов для максимальной производительности MongoDB.
Запустить один раз при инициализации или обновлении системы.
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DatabaseIndexOptimizer:
    """Класс для создания и управления индексами MongoDB."""
    
    def __init__(self, mongodb_url: str, database_name: str):
        self.client = AsyncIOMotorClient(mongodb_url)
        self.db = self.client[database_name]
    
    async def analyze_current_indexes(self):
        """Анализ всех существующих индексов во всех коллекциях."""
        
        print("🔍 Analyzing current MongoDB indexes...")
        print("=" * 80)
        
        # Получаем список всех коллекций
        collections = await self.db.list_collection_names()
        print(f"📋 Found {len(collections)} collections: {', '.join(collections)}\n")
        
        total_indexes = 0
        
        for collection_name in collections:
            collection = self.db[collection_name]
            
            # Получаем информацию об индексах
            indexes = await collection.list_indexes().to_list(length=None)
            
            print(f"📊 Collection: {collection_name}")
            print(f"   Indexes count: {len(indexes)}")
            
            if indexes:
                for idx in indexes:
                    index_name = idx.get('name', 'unnamed')
                    index_keys = idx.get('key', {})
                    index_options = {k: v for k, v in idx.items() if k not in ['name', 'key', 'v', 'ns']}
                    
                    # Форматируем ключи индекса
                    keys_str = ', '.join([f"{k}: {v}" for k, v in index_keys.items()])
                    
                    print(f"   • {index_name}")
                    print(f"     Keys: {{{keys_str}}}")
                    
                    if index_options:
                        options_str = ', '.join([f"{k}: {v}" for k, v in index_options.items()])
                        print(f"     Options: {{{options_str}}}")
                    
                    print()
                
                total_indexes += len(indexes)
            else:
                print("   No indexes found")
            
            print("-" * 60)
        
        print(f"\n📈 Total indexes across all collections: {total_indexes}")
        print("=" * 80)
        
        return collections, total_indexes

    async def create_all_indexes(self):
        """Создание всех оптимальных индексов для максимальной производительности."""
        
        print("🚀 Starting MongoDB index optimization...")
        
        # Сначала анализируем текущие индексы
        await self.analyze_current_indexes()
        
        print("\n🛠️  Creating new optimized indexes...")
        
        # Создаем индексы для каждой коллекции
        await self._create_user_statistics_indexes()
        await self._create_words_indexes()
        await self._create_languages_indexes()
        await self._create_users_indexes()
        await self._create_user_language_settings_indexes()
        
        print("✅ All indexes created successfully!")
        
        # Показываем финальный отчет по индексам
        print("\n🎯 FINAL INDEXES REPORT:")
        await self.analyze_current_indexes()
    
    async def _create_user_statistics_indexes(self):
        """
        КРИТИЧЕСКИЕ индексы для коллекции user_statistics.
        Эти индексы дают максимальный прирост производительности.
        """
        collection = self.db.user_statistics
        print("\n📊 Creating user_statistics indexes...")
        
        indexes_to_create = [
            # 1. ОСНОВНОЙ составной индекс для get_by_user_id
            {
                "keys": [("user_id", 1), ("language_id", 1), ("updated_at", -1)],
                "name": "user_lang_updated_idx",
                "background": True
            },
            
            # 2. УНИКАЛЬНЫЙ индекс для предотвращения дублей статистики
            {
                "keys": [("user_id", 1), ("word_id", 1)],
                "name": "user_word_unique_idx", 
                "unique": True,
                "background": True
            },
            
            # 3. Индекс для get_words_for_review (критичный для производительности)
            {
                "keys": [("user_id", 1), ("language_id", 1), ("next_check_date", 1)],
                "name": "user_lang_review_idx",
                "background": True
            },
            
            # 4. Индекс для подсчета прогресса по score
            {
                "keys": [("user_id", 1), ("language_id", 1), ("score", 1)],
                "name": "user_lang_score_idx", 
                "background": True
            },
            
            # 5. Индекс для фильтрации пропущенных слов
            {
                "keys": [("user_id", 1), ("language_id", 1), ("is_skipped", 1)],
                "name": "user_lang_skipped_idx",
                "background": True
            },
            
            # 6. Индекс для поиска статистики по word_id (для JOIN операций)
            {
                "keys": [("word_id", 1)],
                "name": "word_id_idx",
                "background": True
            },
            
            # 7. Индекс для сортировки по дате обновления (последняя активность)
            {
                "keys": [("user_id", 1), ("updated_at", -1)],
                "name": "user_activity_idx",
                "background": True
            }
        ]
        
        for index_spec in indexes_to_create:
            try:
                await collection.create_index(
                    index_spec["keys"],
                    name=index_spec["name"],
                    background=index_spec.get("background", True),
                    unique=index_spec.get("unique", False)
                )
                print(f"  ✅ Created: {index_spec['name']}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ⚠️  Already exists: {index_spec['name']}")
                else:
                    print(f"  ❌ Error creating {index_spec['name']}: {e}")
    
    async def _create_words_indexes(self):
        """Индексы для коллекции words."""
        collection = self.db.words
        print("\n📝 Creating words indexes...")
        
        indexes_to_create = [
            # 1. Основной индекс для поиска слов по языку и номеру
            {
                "keys": [("language_id", 1), ("word_number", 1)],
                "name": "lang_word_number_idx",
                "background": True
            },
            
            # 2. Индекс для поиска по иностранному слову (уникальность в рамках языка)
            {
                "keys": [("language_id", 1), ("word_foreign", 1)],
                "name": "lang_word_foreign_idx",
                "background": True,
                "unique": True
            },
            
            # 3. Индекс только по language_id для быстрого count
            {
                "keys": [("language_id", 1)],
                "name": "language_id_idx",
                "background": True
            }
        ]
        
        for index_spec in indexes_to_create:
            try:
                await collection.create_index(
                    index_spec["keys"],
                    name=index_spec["name"],
                    background=index_spec.get("background", True),
                    unique=index_spec.get("unique", False)
                )
                print(f"  ✅ Created: {index_spec['name']}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ⚠️  Already exists: {index_spec['name']}")
                else:
                    print(f"  ❌ Error creating {index_spec['name']}: {e}")
    
    async def _create_languages_indexes(self):
        """Индексы для коллекции languages."""
        collection = self.db.languages
        print("\n🌐 Creating languages indexes...")
        
        indexes_to_create = [
            # 1. Индекс для поиска по русскому названию
            {
                "keys": [("name_ru", 1)],
                "name": "name_ru_idx",
                "background": True
            },
            
            # 2. Индекс для поиска по иностранному названию
            {
                "keys": [("name_foreign", 1)],
                "name": "name_foreign_idx", 
                "background": True
            }
        ]
        
        for index_spec in indexes_to_create:
            try:
                await collection.create_index(
                    index_spec["keys"],
                    name=index_spec["name"],
                    background=index_spec.get("background", True)
                )
                print(f"  ✅ Created: {index_spec['name']}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ⚠️  Already exists: {index_spec['name']}")
                else:
                    print(f"  ❌ Error creating {index_spec['name']}: {e}")
    
    async def _create_users_indexes(self):
        """Индексы для коллекции users."""
        collection = self.db.users
        print("\n👥 Creating users indexes...")
        
        indexes_to_create = [
            # 1. УНИКАЛЬНЫЙ индекс по telegram_id (основной поиск пользователей)
            {
                "keys": [("telegram_id", 1)],
                "name": "telegram_id_unique_idx",
                "background": True,
                "unique": True
            },
            
            # 2. Индекс по username
            {
                "keys": [("username", 1)],
                "name": "username_idx",
                "background": True
            },
            
            # 3. Индекс для поиска администраторов
            {
                "keys": [("is_admin", 1)],
                "name": "is_admin_idx",
                "background": True
            }
        ]
        
        for index_spec in indexes_to_create:
            try:
                await collection.create_index(
                    index_spec["keys"],
                    name=index_spec["name"],
                    background=index_spec.get("background", True),
                    unique=index_spec.get("unique", False)
                )
                print(f"  ✅ Created: {index_spec['name']}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ⚠️  Already exists: {index_spec['name']}")
                else:
                    print(f"  ❌ Error creating {index_spec['name']}: {e}")
    
    async def _create_user_language_settings_indexes(self):
        """Индексы для коллекции user_language_settings."""
        collection = self.db.user_language_settings
        print("\n⚙️  Creating user_language_settings indexes...")
        
        indexes_to_create = [
            # 1. УНИКАЛЬНЫЙ составной индекс по пользователю и языку
            {
                "keys": [("user_id", 1), ("language_id", 1)],
                "name": "user_lang_settings_unique_idx",
                "background": True,
                "unique": True
            },
            
            # 2. Индекс для поиска всех настроек пользователя
            {
                "keys": [("user_id", 1)],
                "name": "user_settings_idx",
                "background": True
            }
        ]
        
        for index_spec in indexes_to_create:
            try:
                await collection.create_index(
                    index_spec["keys"],
                    name=index_spec["name"],
                    background=index_spec.get("background", True),
                    unique=index_spec.get("unique", False)
                )
                print(f"  ✅ Created: {index_spec['name']}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ⚠️  Already exists: {index_spec['name']}")
                else:
                    print(f"  ❌ Error creating {index_spec['name']}: {e}")

    async def get_index_usage_stats(self):
        """Получение статистики использования индексов."""
        print("\n📈 INDEX USAGE STATISTICS:")
        print("=" * 80)
        
        collections = await self.db.list_collection_names()
        
        for collection_name in collections:
            collection = self.db[collection_name]
            
            try:
                # Получаем статистику использования индексов
                stats = await self.db.command("collStats", collection_name, indexDetails=True)
                
                print(f"\n📊 Collection: {collection_name}")
                print(f"   Documents: {stats.get('count', 0):,}")
                print(f"   Size: {stats.get('size', 0) / 1024 / 1024:.2f} MB")
                
                # Статистика индексов
                index_sizes = stats.get('indexSizes', {})
                if index_sizes:
                    print("   Index sizes:")
                    for index_name, size in index_sizes.items():
                        print(f"     • {index_name}: {size / 1024 / 1024:.2f} MB")
                
            except Exception as e:
                print(f"   ❌ Error getting stats for {collection_name}: {e}")
    
    async def explain_query_performance(self, collection_name: str, query: dict, sort: dict = None):
        """Анализ производительности конкретного запроса."""
        print(f"\n🔍 QUERY PERFORMANCE ANALYSIS for {collection_name}:")
        print(f"Query: {query}")
        if sort:
            print(f"Sort: {sort}")
        print("-" * 60)
        
        collection = self.db[collection_name]
        
        try:
            # Выполняем explain для запроса
            cursor = collection.find(query)
            if sort:
                cursor = cursor.sort(list(sort.items()))
            
            explain_result = await cursor.explain()
            
            # Извлекаем ключевую информацию
            execution_stats = explain_result.get('executionStats', {})
            
            print(f"Execution time: {execution_stats.get('executionTimeMillis', 0)} ms")
            print(f"Documents examined: {execution_stats.get('totalDocsExamined', 0):,}")
            print(f"Documents returned: {execution_stats.get('totalDocsReturned', 0):,}")
            print(f"Index used: {explain_result.get('queryPlanner', {}).get('winningPlan', {}).get('inputStage', {}).get('indexName', 'NO INDEX')}")
            
            # Проверяем эффективность
            docs_examined = execution_stats.get('totalDocsExamined', 0)
            docs_returned = execution_stats.get('totalDocsReturned', 0)
            
            if docs_examined > 0 and docs_returned > 0:
                efficiency = docs_returned / docs_examined * 100
                print(f"Query efficiency: {efficiency:.1f}%")
                
                if efficiency < 10:
                    print("⚠️  WARNING: Low efficiency! Consider adding indexes.")
                elif efficiency < 50:
                    print("🔶 MODERATE: Query could be optimized.")
                else:
                    print("✅ GOOD: Query is well optimized.")
            
        except Exception as e:
            print(f"❌ Error analyzing query: {e}")

    async def close(self):
        """Закрытие соединения с БД."""
        await self.client.close()

# Функция для быстрого запуска анализа
async def analyze_database_indexes(mongodb_url: str = "mongodb://localhost:8527", 
                                 database_name: str = "language_learning_bot"):
    """Быстрая функция для анализа текущих индексов."""
    
    optimizer = DatabaseIndexOptimizer(mongodb_url, database_name)
    
    try:
        # Анализируем текущие индексы
        await optimizer.analyze_current_indexes()
        
        # Получаем статистику использования
        await optimizer.get_index_usage_stats()
        
        # Примеры анализа критичных запросов
        print("\n🎯 ANALYZING CRITICAL QUERIES:")
        
        # 1. Запрос статистики пользователя
        await optimizer.explain_query_performance(
            "user_statistics",
            {"user_id": "example_user", "language_id": "example_lang"},
            {"updated_at": -1}
        )
        
        # 2. Запрос слов для изучения
        await optimizer.explain_query_performance(
            "words", 
            {"language_id": "example_lang", "word_number": {"$gte": 1}},
            {"word_number": 1}
        )
        
    finally:
        await optimizer.close()

# Функция для создания оптимальных индексов
async def optimize_database_indexes(mongodb_url: str = "mongodb://localhost:8527",
                                  database_name: str = "language_learning_bot"):
    """Создание всех оптимальных индексов."""
    
    optimizer = DatabaseIndexOptimizer(mongodb_url, database_name)
    
    try:
        await optimizer.create_all_indexes()
    finally:
        await optimizer.close()

# Простой синхронный runner для удобства
def run_analysis():
    """Синхронный запуск анализа индексов."""
    asyncio.run(analyze_database_indexes())

def run_optimization():
    """Синхронный запуск создания индексов."""
    asyncio.run(optimize_database_indexes())

if __name__ == "__main__":
    print("💡 MongoDB Index Optimizer")
    print("=" * 50)
    print("Available functions:")
    print("  run_analysis() - анализ текущих индексов")
    print("  run_optimization() - создание оптимальных индексов")
    print()
    print("Or use async versions:")
    print("  analyze_database_indexes()")
    print("  optimize_database_indexes()")
    
    # Раскомментируйте нужную функцию:
    run_analysis()
    # run_optimization()
