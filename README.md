# Voice Bot Creation Pipeline  
Scrape your own Discord messages, turn them into chat-style training pairs, fine-tune GPT-3.5, and get a custom model.

---

## What’s in this repo

| File | Purpose |
|------|---------|
| **dump_mine.py** | Scrapes every text channel the bot can read. |
| **fetch_one.py** | Scrapes one text channel; use if dump_mine fails on a large channel e.g. `#general`). |
| **make_pairs.py** | Builds call/response JSONL pairs with a scoring heuristic; outputs **`pairs.jsonl`**. |
| **raw_dump/** | Folder that will contain `.jsonl.gz` dumps (generated). |
| **pairs.jsonl** | Training data for OpenAI fine-tune (generated). |
| **requirements.txt** | Minimal Python deps (`discord.py`, `python-dateutil`, `pytz`). |

---

## ⚙️ Prereqs

* Python 3.10 +
* Discord bot with **MESSAGE CONTENT** intent  
  (`DISCORD_TOKEN` env var)
* OpenAI key (`OPENAI_API_KEY` env var)

Set your own Discord user ID in `USER_ID` env var.

---

## 🚀 Quick Start

```bash
# 1  install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2  scrape all channels
python dump_mine.py
(python fetch_one.py if a channel fails)

# 3  build training pairs
python make_pairs.py        # → pairs.jsonl

# 4  fine-tune
openai tools fine_tunes.prepare_data -f pairs.jsonl --format chat
openai fine_tunes.create \
      -t pairs_prepared.jsonl \
      -m gpt-3.5-turbo \
      --suffix "[put your model name here]"
