# fetch_one.py
# For fetching a single channel if it's large and problematic
import asyncio, os, json, gzip, pytz, discord, sys, async_timeout
from pathlib import Path
from datetime import timezone

TOKEN   = os.getenv("DISCORD_BOT_TOKEN")
UID     = int(os.getenv("USER_ID"))
GUILDID = 0           # add public guild ID here
CHANID  = 0           # add channel ID (right-click -> Copy ID)
BATCH   = 100
TIMEOUT = 20          # seconds per call
MAX_RETRY = 6
SLEEP   = 1
OUTDIR  = Path("raw_dump")

client = discord.Client(intents=discord.Intents.all())

def make_row(m: discord.Message):
    return {
        "id": m.id,
        "ts": m.created_at.astimezone(pytz.UTC).isoformat(),
        "chan_id": CHANID,
        "author_id": m.author.id,
        "content": m.clean_content,
        "has_attach": bool(m.attachments),
        "attach_types": [a.content_type for a in m.attachments],
        "ref_id": m.reference.message_id if m.reference else None,
    }

async def safe_fetch(chan, before):
    """Fetch one channel with timeout + retry."""
    tries = 0
    while True:
        try:
            async with async_timeout.timeout(TIMEOUT):
                return [m async for m in chan.history(
                                    limit=BATCH,
                                    before=before,
                                    oldest_first=False)]
        except (discord.HTTPException,
                asyncio.TimeoutError) as e:
            tries += 1
            if tries > MAX_RETRY:
                raise RuntimeError(f"Too many retries: {e}") from e
            wait = 2 ** tries
            print(f"[retry {tries}/{MAX_RETRY}] waiting {wait}s ⇒ {e}")
            await asyncio.sleep(wait)

@client.event
async def on_ready():
    guild = client.get_guild(GUILDID)
    chan  = guild.get_channel(CHANID)
    if not chan:
        print("Channel not found.")
        await client.close(); return

    print(f"Fetching {guild.name}#{chan.name} ({BATCH}-msg pages)…")
    rows, before, page = [], None, 0

    while True:
        batch = await safe_fetch(chan, before)
        if not batch:
            print("Reached beginning of channel — done.")
            break

        page += 1
        yours = sum(m.author.id == UID for m in batch)
        cutoff = batch[-1].created_at.strftime("%Y-%m-%d")
        print(f"Page {page:>4}: {len(batch):3} msgs, "
              f"{yours:2} yours  | next < {cutoff}", flush=True)

        rows.extend(make_row(m) for m in batch)
        before = batch[-1]          # advance with OLDEST message object
        await asyncio.sleep(SLEEP)

    # write file
    OUTDIR.mkdir(exist_ok=True)
    fname = OUTDIR / f"{GUILDID}_{CHANID}.jsonl.gz"
    with gzip.open(fname, "wt", encoding="utf8") as f:
        for r in reversed(rows):    # oldest → newest
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(rows):,} total messages "
          f"({sum(r['author_id']==UID for r in rows):,} yours) → {fname}")
    await client.close(); sys.exit(0)

asyncio.run(client.start(TOKEN))