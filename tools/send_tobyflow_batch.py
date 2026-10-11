import tomllib
import subprocess
import time

with open("jobs/2026-07-21_001_gi-tr-quy-t-nh-thu-nh-p/source/creative_plan.toml", "rb") as f:
    data = tomllib.load(f)

scenes = data.get("scene_intents", [])
print(f"Sending {len(scenes)} scene prompts to TobyFlow CLI...")

for sc in scenes:
    sc_id = sc["id"]
    prompt = sc["visual_intent"]
    print(f"\n[+] Sending {sc_id}: {prompt[:70]}...")
    cmd = ["node", r"E:\1.1.0_0\telegram-bridge\cli.js", "image", prompt, "--ratio", "9:16"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    print(res.stdout.strip())
    time.sleep(1)

print("\nAll 10 prompts sent to TobyFlow! Sending RUN command...")
cmd_run = ["node", r"E:\1.1.0_0\telegram-bridge\cli.js", "run"]
res_run = subprocess.run(cmd_run, capture_output=True, text=True, encoding="utf-8")
print(res_run.stdout.strip())
