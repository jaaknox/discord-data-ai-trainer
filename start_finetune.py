# start_finetune.py
# THANK YOU OPENAI!
import openai
import os

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

job_id = "" # Job ID goes here

events = client.fine_tuning.jobs.list_events(job_id)

for event in reversed(events.data):
    print(f"[{event.created_at}] {event.message}")
