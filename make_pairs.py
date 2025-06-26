# make_pairs.py
# build high-quality prompt/response pairs
import os, json, gzip, glob, re
from pathlib import Path
from datetime import timedelta
from dateutil.parser import isoparse

UID = int(os.getenv("USER_ID"))

RAW_DIR            = Path("raw_dump")
OUT_FILE           = Path("pairs.jsonl")
JOIN_WINDOW_SEC    = 90                        # merge messages send <= 90 s apart
MAX_SEARCH_WINDOW  = timedelta(seconds=90)     # look this far back for prompt
MAX_REPLY_CHARS    = 600                       # truncate very long answers
MIN_PROMPT_SCORE   = 1                         # skip bursts w/ ambiguous context

QUESTION_WORDS = {"who", "what", "when", "where", "why", "how"}

# ───────────────────────────  scoring rules  ────────────────────────────
def score(msg, mention_tag):
    """
    Higher score ⇒ more likely user was answering this msg.
    Only non-user messages are evaluated.
    """
    if msg["author_id"] == UID:
        return -99
    text = msg["content"].lower()

    s = 0
    if text.endswith("?"):                         s += 3
    elif "?" in text:                              s += 2
    if any(w in text for w in QUESTION_WORDS):     s += 3
    if mention_tag and mention_tag in text: s += 3
    if len(text.split()) < 5 and "?" not in text:  s -= 1
    if msg["has_attach"] and not text:             s -= 3
    return s

def clean(txt):
    return txt.strip()[:MAX_REPLY_CHARS]

pairs = []
for gz in glob.glob(str(RAW_DIR / "*.jsonl.gz")):
    with gzip.open(gz, "rt", encoding="utf8") as f:
        rows = [json.loads(line) for line in f]

    id_lookup = {r["id"]: r for r in rows}

    i = 0
    while i < len(rows):
        cur = rows[i]
        if cur["author_id"] != UID or not cur["content"].strip():
            i += 1
            continue

        # merge consecutive lines into one burst
        burst_lines = [clean(cur["content"])]
        burst_start_ts = isoparse(cur["ts"])
        k = i + 1
        while k < len(rows):
            nxt = rows[k]
            if nxt["author_id"] != UID:
                break
            gap = isoparse(nxt["ts"]) - isoparse(rows[k-1]["ts"])
            if gap.total_seconds() > JOIN_WINDOW_SEC:
                break
            if nxt["content"].strip():
                burst_lines.append(clean(nxt["content"]))
            k += 1
        assistant_reply = "\n".join(burst_lines)

        # pick the best prompt for this burst
        prompt_text = None
        best_score = -99

        # explicit Discord reply pointer
        if cur["ref_id"]:
            ref = id_lookup.get(cur["ref_id"])
            if ref and ref["author_id"] != UID and ref["content"].strip():
                prompt_text = clean(ref["content"])
                best_score = 99     # cannot be beaten

        # otherwise, rank messages in the look-back window
        if best_score < 0:
            user_tag = f"<@{UID}>"
            j = i - 1
            while j >= 0:
                cand = rows[j]
                delta = burst_start_ts - isoparse(cand["ts"])
                if delta > MAX_SEARCH_WINDOW:
                    break
                sc = score(cand, user_tag)
                if sc > best_score:
                    best_score = sc
                    prompt_text = clean(cand["content"])
                j -= 1

        # skip if no good prompt found
        if best_score < MIN_PROMPT_SCORE or not prompt_text:
            i = k
            continue

        pairs.append({"messages": [
            {"role": "user",      "content": prompt_text},
            {"role": "assistant", "content": assistant_reply}
        ]})

        i = k 

OUT_FILE.write_text(
    "\n".join(json.dumps(p, ensure_ascii=False) for p in pairs),
    encoding="utf8"
)
print(f"Built {len(pairs):,} prompt-response pairs → {OUT_FILE}")
