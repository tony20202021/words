"""Load Hebrew 10000-word frequency dictionary into language_learning_bot MongoDB.
Idempotent: safe to re-run. Also builds an .xlsx for admin upload."""
import asyncio, json, os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

URL=os.getenv("MONGODB_URL","mongodb://localhost:8527")
DB=os.getenv("MONGODB_DB_NAME","language_learning_bot")
DATA="/home/tony/repos/words/words/data/hebrew_freq/hebrew_freq_10000_full.json"
NAME_RU="Иврит"; NAME_FOREIGN="עברית"

def compute_unit_count(text):
    if not text: return None
    text=text.strip()
    if not text: return None
    if any('一'<=c<='鿿' for c in text): return len(text)
    return len(text.split())

def transcription_of(r):
    return f"/{r['ipa']}/\n{r['translit_ru']}"

async def main():
    rows=json.load(open(DATA,encoding="utf-8"))
    db=AsyncIOMotorClient(URL)[DB]
    lang=await db.languages.find_one({"name_ru":NAME_RU})
    if lang:
        lang_id=lang["_id"]; print(f"language exists: {NAME_RU} id={lang_id}")
    else:
        now=datetime.utcnow()
        res=await db.languages.insert_one({"name_ru":NAME_RU,"name_foreign":NAME_FOREIGN,
                                           "created_at":now,"updated_at":now})
        lang_id=res.inserted_id; print(f"CREATED language {NAME_RU}/{NAME_FOREIGN} id={lang_id}")

    existing=await db.words.count_documents({"language_id":lang_id})
    print(f"existing words for language: {existing}")
    inserted=skipped=0
    docs=[]
    for r in rows:
        trans=transcription_of(r)
        doc={"language_id":lang_id,"word_number":r["rank"],
             "word_foreign":r["hebrew"],"translation":r["russian"],
             "transcription":trans,"sound_file_path":"",
             "word_foreign_unit_count":compute_unit_count(r["hebrew"]),
             "transcription_unit_count":compute_unit_count(trans),
             "created_at":datetime.utcnow(),"updated_at":datetime.utcnow()}
        if existing:
            ex=await db.words.find_one({"language_id":lang_id,"word_number":r["rank"]})
            if ex: skipped+=1; continue
            await db.words.insert_one(doc); inserted+=1
        else:
            docs.append(doc)
    if docs:
        await db.words.insert_many(docs); inserted=len(docs)
    total=await db.words.count_documents({"language_id":lang_id})
    print(f"inserted={inserted} skipped={skipped} | total now={total}")
    # verify sample
    for wn in [1,232,5000,10000]:
        d=await db.words.find_one({"language_id":lang_id,"word_number":wn})
        if d: print(f"  №{wn}: {d['word_foreign']} | {d['transcription']!r} | {d['translation']}")

asyncio.run(main())
