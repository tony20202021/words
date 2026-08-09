import os, glob, asyncio, json, time
from gtts import gTTS
import edge_tts
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from motor.motor_asyncio import AsyncIOMotorClient

BASE="/home/tony/repos/words/language-learning-bot/backend/data/sounds/he"
for s in ["gtts","hila","avri"]: os.makedirs(f"{BASE}/{s}", exist_ok=True)
D="/home/tony/repos/words/words/data/hebrew_freq/"
rows={r["rank"]:r for r in json.load(open(D+"hebrew_freq_10000_full.json",encoding="utf-8"))}
LO,HI=1001,10000
LOG=open(D+"gen_sounds_rest.log","w")
def log(m): LOG.write(m+"\n"); LOG.flush()

def trim(fp, thr=-40.0, keep=40):
    try:
        seg=AudioSegment.from_file(fp)
        lead=detect_leading_silence(seg, silence_threshold=thr)
        trail=detect_leading_silence(seg.reverse(), silence_threshold=thr)
        start=max(0, lead-keep); end=len(seg)-max(0, trail-keep)
        if end>start: seg[start:end].export(fp, format="mp3", bitrate="48k")
    except Exception as e: log(f"  trim fail {fp}: {e}")

def gtts_save(text, fp, tries=3):
    for i in range(tries):
        try:
            gTTS(text=text, lang='iw', slow=False).save(fp)
            if os.path.getsize(fp)>0: return True
        except Exception: time.sleep(1.5*(i+1))
    return False

async def edge_save(text, voice, fp, tries=3):
    for i in range(tries):
        try:
            await edge_tts.Communicate(text, voice).save(fp)
            if os.path.exists(fp) and os.path.getsize(fp)>0: return True
        except Exception: await asyncio.sleep(1.5*(i+1))
    return False

async def main():
    t0=time.time(); fails=[]
    for n in range(LO,HI+1):
        w=rows[n]["hebrew"]
        fg=f"{BASE}/gtts/{n}.mp3"; fh=f"{BASE}/hila/{n}.mp3"; fa=f"{BASE}/avri/{n}.mp3"
        if not (os.path.exists(fg) and os.path.getsize(fg)>0):
            if gtts_save(w, fg): trim(fg)
            else: fails.append(("gtts",n))
        if not (os.path.exists(fh) and os.path.getsize(fh)>0):
            if await edge_save(w,"he-IL-HilaNeural",fh): trim(fh)
            else: fails.append(("hila",n))
        if not (os.path.exists(fa) and os.path.getsize(fa)>0):
            if await edge_save(w,"he-IL-AvriNeural",fa): trim(fa)
            else: fails.append(("avri",n))
        if n%100==0: log(f"{n}/{HI} ({time.time()-t0:.0f}s) fails={len(fails)}")
    log(f"generation done. fails={len(fails)}: {fails[:30]}")
    db=AsyncIOMotorClient("mongodb://localhost:8527")["language_learning_bot"]
    lid=(await db.languages.find_one({"name_ru":"Иврит"}))["_id"]
    for n in range(LO,HI+1):
        sounds=json.dumps({"sound_1":f"sounds/he/gtts/{n}.mp3",
                           "sound_2":f"sounds/he/hila/{n}.mp3",
                           "sound_3":f"sounds/he/avri/{n}.mp3"}, ensure_ascii=False)
        await db.words.update_one({"language_id":lid,"word_number":n},{"$set":{"sounds":sounds}})
    # remove flat orphans in range
    for fp in glob.glob(BASE+"/*.mp3"):
        b=os.path.splitext(os.path.basename(fp))[0]
        if b.isdigit() and LO<=int(b)<=HI: os.remove(fp)
    log("DB updated + orphans removed. ALL DONE")
asyncio.run(main())
