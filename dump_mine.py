# dump_mine.py
import asyncio, json, os, gzip, pytz, discord, signal, sys
from pathlib import Path

TOKEN  = os.getenv("DISCORD_BOT_TOKEN")
UID    = int(os.getenv("USER_ID"))
OUT    = Path("raw_dump")
SKIP_CHANS = {}                             # skip any channel IDs with mostly useless data like bot commands
INTENTS = discord.Intents.all()
client  = discord.Client(intents=INTENTS)

stop_now = False
def _sigint(_, __):
    global stop_now; stop_now = True
signal.signal(signal.SIGINT, _sigint)

def make_row(m: discord.Message):
    return {
        "id": m.id,
        "ts": m.created_at.astimezone(pytz.UTC).isoformat(),
        "chan_id": m.channel.id,
        "author_id": m.author.id,
        "content": m.clean_content,
        "has_attach": bool(m.attachments),
        "attach_types": [a.content_type for a in m.attachments],
        "ref_id": m.reference.message_id if m.reference else None,
    }

@client.event
async def on_ready():
    OUT.mkdir(exist_ok=True)
    for guild in client.guilds:
        if stop_now: break
        print(f"\n=== {guild.name} ===")
        for chan in guild.text_channels:
            if stop_now: break
            if chan.id in SKIP_CHANS:
                print(f"[skipping] #{chan.name}")
                continue
            if not chan.permissions_for(guild.me).read_message_history:
                print(f"[skip perms]  #{chan.name}")
                continue

            rows, counter = [], 0
            try:
                async for m in chan.history(limit=None, oldest_first=True):
                    if stop_now: break
                    rows.append(make_row(m))
                    counter += 1
                    if counter % 2000 == 0:
                        await asyncio.sleep(1)
            except discord.HTTPException as e:
                print(f"[error] #{chan.name}: {e}")
                continue

            if not rows:
                print(f"#{chan.name}: 0 msgs – skipped")
                continue

            fname = OUT / f"{guild.id}_{chan.id}.jsonl.gz"
            with gzip.open(fname, "wt", encoding="utf8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"#{chan.name}: saved {len(rows):,} msgs "
                  "(everyone's)")

    await client.close()
    if stop_now:
        print("\nInterrupted but finished channels were saved.")

asyncio.run(client.start(TOKEN))
