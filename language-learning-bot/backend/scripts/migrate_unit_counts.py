"""Populate word_foreign_unit_count and transcription_unit_count for all existing words."""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")
DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")


def _compute_unit_count(text):
    if not text:
        return None
    text = text.strip()
    if not text:
        return None
    if any('一' <= c <= '鿿' for c in text):
        return len(text)
    return len(text.split())


async def migrate():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db.words

    total = await collection.count_documents({})
    print(f"Total words: {total}")

    updated = 0
    async for word in collection.find({}, {"word_foreign": 1, "transcription": 1}):
        fuc = _compute_unit_count(word.get("word_foreign"))
        tuc = _compute_unit_count(word.get("transcription"))
        await collection.update_one(
            {"_id": word["_id"]},
            {"$set": {"word_foreign_unit_count": fuc, "transcription_unit_count": tuc}}
        )
        updated += 1
        if updated % 100 == 0:
            print(f"Updated {updated}/{total}")

    print(f"Done. Updated {updated} words.")
    client.close()


asyncio.run(migrate())
