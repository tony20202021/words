"""
Скрипт для просмотра всех баз данных и коллекций в MongoDB
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any

class MongoDBExplorer:
    """Класс для исследования структуры MongoDB."""
    
    def __init__(self, mongodb_url: str = "mongodb://localhost:8527"):
        self.client = AsyncIOMotorClient(mongodb_url)
    
    async def list_all_databases(self):
        """Показать все базы данных."""
        print("📊 MONGODB DATABASES:")
        print("=" * 60)
        
        try:
            # Получаем список всех баз данных
            db_list = await self.client.list_database_names()
            
            print(f"Found {len(db_list)} databases:\n")
            
            for db_name in db_list:
                db = self.client[db_name]
                
                try:
                    # Получаем статистику базы данных
                    stats = await db.command("dbStats")
                    
                    size_mb = stats.get('dataSize', 0) / 1024 / 1024
                    collections_count = stats.get('collections', 0)
                    
                    print(f"📁 {db_name}")
                    print(f"   Size: {size_mb:.2f} MB")
                    print(f"   Collections: {collections_count}")
                    
                    # Показываем коллекции
                    collections = await db.list_collection_names()
                    if collections:
                        print(f"   └── Collections: {', '.join(collections)}")
                    print()
                    
                except Exception as e:
                    print(f"📁 {db_name}")
                    print(f"   ❌ Error getting stats: {e}")
                    print()
            
        except Exception as e:
            print(f"❌ Error listing databases: {e}")
    
    async def explore_database(self, db_name: str, show_fields: bool = True, sample_size: int = 100):
        """Детальное исследование конкретной базы данных."""
        print(f"🔍 EXPLORING DATABASE: {db_name}")
        print("=" * 80)
        
        db = self.client[db_name]
        
        try:
            # Статистика базы данных
            stats = await db.command("dbStats")
            
            print(f"Database: {db_name}")
            print(f"Data Size: {stats.get('dataSize', 0) / 1024 / 1024:.2f} MB")
            print(f"Storage Size: {stats.get('storageSize', 0) / 1024 / 1024:.2f} MB")
            print(f"Index Size: {stats.get('indexSize', 0) / 1024 / 1024:.2f} MB")
            print(f"Collections: {stats.get('collections', 0)}")
            print(f"Documents: {stats.get('objects', 0):,}")
            print()
            
            # Детальная информация по коллекциям
            collections = await db.list_collection_names()
            
            for collection_name in collections:
                collection = db[collection_name]
                
                try:
                    # Статистика коллекции
                    coll_stats = await db.command("collStats", collection_name)
                    
                    print(f"📊 Collection: {collection_name}")
                    print(f"   Documents: {coll_stats.get('count', 0):,}")
                    print(f"   Size: {coll_stats.get('size', 0) / 1024 / 1024:.2f} MB")
                    print(f"   Avg doc size: {coll_stats.get('avgObjSize', 0):.0f} bytes")
                    
                    # Индексы
                    indexes = await collection.list_indexes().to_list(length=None)
                    print(f"   Indexes: {len(indexes)}")
                    for idx in indexes:
                        idx_name = idx.get('name', 'unnamed')
                        idx_keys = list(idx.get('key', {}).keys())
                        print(f"     • {idx_name}: {', '.join(idx_keys)}")
                    
                    # НОВОЕ: Анализ полей и типов
                    if show_fields:
                        await self._analyze_collection_schema(collection, collection_name, sample_size)
                    
                    print()
                    
                except Exception as e:
                    print(f"📊 Collection: {collection_name}")
                    print(f"   ❌ Error: {e}")
                    print()
            
        except Exception as e:
            print(f"❌ Error exploring database: {e}")
    
    async def _analyze_collection_schema(self, collection, collection_name: str, sample_size: int = 100):
        """Анализ схемы коллекции - поля и типы данных."""
        print(f"   📋 Schema Analysis (sample size: {sample_size}):")
        
        try:
            # Получаем sample документов для анализа
            sample_docs = await collection.aggregate([
                {"$sample": {"size": sample_size}},
                {"$limit": sample_size}
            ]).to_list(length=sample_size)
            
            if not sample_docs:
                print("     ⚠️  No documents found")
                return
            
            # Анализируем поля и типы
            field_analysis = {}
            
            for doc in sample_docs:
                self._analyze_document_fields(doc, field_analysis, "")
            
            # Выводим результаты анализа
            self._print_field_analysis(field_analysis, len(sample_docs))
            
        except Exception as e:
            print(f"     ❌ Schema analysis error: {e}")
    
    def _analyze_document_fields(self, doc: dict, field_analysis: dict, prefix: str = ""):
        """Рекурсивный анализ полей документа."""
        for key, value in doc.items():
            field_path = f"{prefix}.{key}" if prefix else key
            
            # Определяем тип значения
            field_type = self._get_field_type(value)
            
            # Инициализируем или обновляем анализ поля
            if field_path not in field_analysis:
                field_analysis[field_path] = {
                    'types': {},
                    'null_count': 0,
                    'sample_values': set(),
                    'min_length': None,
                    'max_length': None
                }
            
            field_info = field_analysis[field_path]
            
            # Подсчитываем типы
            if value is None:
                field_info['null_count'] += 1
            else:
                if field_type not in field_info['types']:
                    field_info['types'][field_type] = 0
                field_info['types'][field_type] += 1
                
                # Добавляем примеры значений (ограниченно)
                if len(field_info['sample_values']) < 3:
                    if isinstance(value, (str, int, float, bool)):
                        field_info['sample_values'].add(str(value)[:50])
                
                # Анализируем длину для строк
                if isinstance(value, str):
                    length = len(value)
                    if field_info['min_length'] is None or length < field_info['min_length']:
                        field_info['min_length'] = length
                    if field_info['max_length'] is None or length > field_info['max_length']:
                        field_info['max_length'] = length
                
                # Рекурсивно анализируем вложенные объекты
                if isinstance(value, dict):
                    self._analyze_document_fields(value, field_analysis, field_path)
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    # Анализируем первый элемент массива объектов
                    self._analyze_document_fields(value[0], field_analysis, f"{field_path}[]")
    
    def _get_field_type(self, value):
        """Определение типа поля."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            if not value:
                return "array(empty)"
            else:
                element_type = self._get_field_type(value[0])
                return f"array({element_type})"
        elif isinstance(value, dict):
            return "object"
        elif hasattr(value, '__class__') and 'ObjectId' in str(type(value)):
            return "ObjectId"
        elif hasattr(value, '__class__') and 'datetime' in str(type(value)):
            return "datetime"
        else:
            return str(type(value).__name__)
    
    def _print_field_analysis(self, field_analysis: dict, total_docs: int):
        """Вывод результатов анализа полей."""
        # Сортируем поля по имени
        sorted_fields = sorted(field_analysis.items())
        
        for field_path, field_info in sorted_fields:
            # Подсчитываем частоту появления поля
            total_non_null = sum(field_info['types'].values())
            frequency = (total_non_null / total_docs) * 100
            
            # Основная информация о поле
            print(f"     🔸 {field_path}")
            print(f"       Frequency: {frequency:.1f}% ({total_non_null}/{total_docs})")
            
            # Типы данных
            if field_info['types']:
                types_str = ', '.join([f"{t}({c})" for t, c in field_info['types'].items()])
                print(f"       Types: {types_str}")
            
            # Null значения
            if field_info['null_count'] > 0:
                null_pct = (field_info['null_count'] / total_docs) * 100
                print(f"       Nulls: {field_info['null_count']} ({null_pct:.1f}%)")
            
            # Длина строк
            if field_info['min_length'] is not None:
                print(f"       Length: {field_info['min_length']}-{field_info['max_length']} chars")
            
            # Примеры значений
            if field_info['sample_values']:
                examples = ', '.join(list(field_info['sample_values'])[:3])
                print(f"       Examples: {examples}")
            
            print()
    
    async def analyze_collection_detailed(self, db_name: str, collection_name: str, sample_size: int = 500):
        """Детальный анализ конкретной коллекции."""
        print(f"🔬 DETAILED COLLECTION ANALYSIS: {db_name}.{collection_name}")
        print("=" * 80)
        
        db = self.client[db_name]
        collection = db[collection_name]
        
        try:
            # Базовая статистика
            total_docs = await collection.count_documents({})
            print(f"Total documents: {total_docs:,}")
            
            if total_docs == 0:
                print("⚠️  Collection is empty")
                return
            
            # Статистика коллекции
            coll_stats = await db.command("collStats", collection_name)
            print(f"Collection size: {coll_stats.get('size', 0) / 1024 / 1024:.2f} MB")
            print(f"Average document size: {coll_stats.get('avgObjSize', 0):.0f} bytes")
            print()
            
            # Анализ схемы
            await self._analyze_collection_schema(collection, collection_name, min(sample_size, total_docs))
            
            # Показываем несколько примеров документов
            print(f"📄 Sample Documents (first 2):")
            sample_docs = await collection.find().limit(2).to_list(length=2)
            
            for i, doc in enumerate(sample_docs, 1):
                print(f"   Document {i}:")
                self._print_document_pretty(doc, indent="     ")
                print()
            
        except Exception as e:
            print(f"❌ Error analyzing collection: {e}")
    
    def _print_document_pretty(self, doc: dict, indent: str = ""):
        """Красивый вывод документа."""
        for key, value in doc.items():
            if isinstance(value, dict):
                print(f"{indent}{key}: {{")
                self._print_document_pretty(value, indent + "  ")
                print(f"{indent}}}")
            elif isinstance(value, list):
                print(f"{indent}{key}: [{len(value)} items]")
                if value and not isinstance(value[0], (dict, list)):
                    preview = str(value[:3])[1:-1]  # Показываем первые 3 элемента
                    print(f"{indent}  Preview: {preview}")
            else:
                # Ограничиваем длинные значения
                str_value = str(value)
                if len(str_value) > 50:
                    str_value = str_value[:47] + "..."
                print(f"{indent}{key}: {str_value} ({type(value).__name__})")
    
    async def show_database_sizes(self):
        """Показать размеры всех баз данных."""
        print("📏 DATABASE SIZES:")
        print("=" * 40)
        
        try:
            db_list = await self.client.list_database_names()
            
            total_size = 0
            db_sizes = []
            
            for db_name in db_list:
                db = self.client[db_name]
                try:
                    stats = await db.command("dbStats")
                    size_mb = stats.get('dataSize', 0) / 1024 / 1024
                    db_sizes.append((db_name, size_mb))
                    total_size += size_mb
                except:
                    db_sizes.append((db_name, 0))
            
            # Сортируем по размеру
            db_sizes.sort(key=lambda x: x[1], reverse=True)
            
            for db_name, size_mb in db_sizes:
                percentage = (size_mb / total_size * 100) if total_size > 0 else 0
                print(f"{db_name:25} {size_mb:8.2f} MB ({percentage:5.1f}%)")
            
            print("-" * 40)
            print(f"{'TOTAL':25} {total_size:8.2f} MB")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def close(self):
        """Закрыть соединение."""
        self.client.close()

# Функции для быстрого использования
async def show_all_databases(mongodb_url: str = "mongodb://localhost:8527"):
    """Показать все базы данных."""
    explorer = MongoDBExplorer(mongodb_url)
    try:
        await explorer.list_all_databases()
    finally:
        await explorer.close()

async def explore_specific_database(db_name: str, mongodb_url: str = "mongodb://localhost:8527", show_fields: bool = True):
    """Исследовать конкретную базу данных."""
    explorer = MongoDBExplorer(mongodb_url)
    try:
        await explorer.explore_database(db_name, show_fields=show_fields)
    finally:
        await explorer.close()

async def analyze_collection(db_name: str, collection_name: str, mongodb_url: str = "mongodb://localhost:8527", sample_size: int = 500):
    """Детальный анализ конкретной коллекции."""
    explorer = MongoDBExplorer(mongodb_url)
    try:
        await explorer.analyze_collection_detailed(db_name, collection_name, sample_size)
    finally:
        await explorer.close()

async def show_database_sizes(mongodb_url: str = "mongodb://localhost:8527"):
    """Показать размеры баз данных."""
    explorer = MongoDBExplorer(mongodb_url)
    try:
        await explorer.show_database_sizes()
    finally:
        await explorer.close()

# Синхронные обертки
def list_databases():
    """Синхронная версия для просмотра всех БД."""
    asyncio.run(show_all_databases())

def explore_database(db_name: str, show_fields: bool = True):
    """Синхронная версия для исследования БД."""
    asyncio.run(explore_specific_database(db_name, show_fields=show_fields))

def analyze_collection(db_name: str, collection_name: str, sample_size: int = 500):
    """Синхронная версия для детального анализа коллекции."""
    asyncio.run(analyze_collection(db_name, collection_name, sample_size=sample_size))

def database_sizes():
    """Синхронная версия для размеров БД."""
    asyncio.run(show_database_sizes())

if __name__ == "__main__":
    print("💡 MongoDB Database Explorer")
    print("=" * 40)
    print("Available functions:")
    print("  list_databases() - показать все БД")
    print("  explore_database('db_name', show_fields=True) - исследовать БД с полями")
    print("  analyze_collection('db_name', 'collection_name') - детальный анализ коллекции")
    print("  database_sizes() - размеры БД")
    print()
    print("Examples:")
    print("  explore_database('language_learning_bot')")
    print("  analyze_collection('language_learning_bot', 'user_statistics')")
    print()
    
    # Раскомментируйте нужную функцию:
    # list_databases()
    explore_database("language_learning_bot")
    # analyze_collection("language_learning_bot", "user_statistics")
    # database_sizes()
