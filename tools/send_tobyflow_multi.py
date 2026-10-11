import tomllib
import subprocess
import time

PLAN_PATH = "jobs/2026-07-21_001_gi-tr-quy-t-nh-thu-nh-p/source/creative_plan.toml"
CLI_PATH = r"E:\1.1.0_0\telegram-bridge\cli.js"

with open(PLAN_PATH, "rb") as f:
    plan = tomllib.load(f)

scenes = plan.get("scene_intents", [])
prompts = [sc["visual_intent"] for sc in scenes]

joined_prompts = "\n\n".join(prompts)

print(f"Sending batch of {len(prompts)} prompts to TobyFlow in MULTI mode...")

cmd_img = ["node", CLI_PATH, "image", joined_prompts, "--ratio", "9:16", "--mode", "multi"]
res = subprocess.run(cmd_img, capture_output=True, text=True, encoding="utf-8")
print(res.stdout.strip())

time.sleep(1)

cmd_run = ["node", CLI_PATH, "run"]
res_run = subprocess.run(cmd_run, capture_output=True, text=True, encoding="utf-8")
print(res_run.stdout.strip())

# Trigger Alt+G in Chrome to ensure TobyFlow processes the multi batch
ps_cmd = '$wshell = New-Object -ComObject WScript.Shell; $wshell.AppActivate(4952); Start-Sleep -Milliseconds 300; $wshell.SendKeys("%g")'
subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)

print("✅ Multi-prompt batch submitted successfully!")
