import tomllib
import os
import glob
import shutil
import time
import subprocess

JOB_DIR = "jobs/2026-07-21_001_gi-tr-quy-t-nh-thu-nh-p"
PLAN_PATH = os.path.join(JOB_DIR, "source/creative_plan.toml")
RAW_IMG_DIR = os.path.join(JOB_DIR, "input/raw_assets/images")
DOWNLOAD_DIR = r"C:\Users\Home\Downloads\tobyflow_output\tobyflow_bot"
CLI_PATH = r"E:\1.1.0_0\telegram-bridge\cli.js"

os.makedirs(RAW_IMG_DIR, exist_ok=True)

with open(PLAN_PATH, "rb") as f:
    plan = tomllib.load(f)

scenes = plan.get("scene_intents", [])

print(f"Loaded {len(scenes)} scenes from creative_plan.toml")

for sc in scenes:
    sc_id = sc["id"]
    prompt = sc["visual_intent"]
    dest_path = os.path.join(RAW_IMG_DIR, f"{sc_id}.jpeg")

    if os.path.exists(dest_path):
        print(f"✓ Scene {sc_id} already exists ({dest_path}). Skipping.")
        continue

    print(f"\n==========================================")
    print(f"Processing {sc_id}...")
    print(f"Prompt: {prompt[:70]}...")
    print(f"==========================================")

    # Record files before download
    before_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.jpeg")))

    # 1. Send image prompt to CLI
    cmd_img = ["node", CLI_PATH, "image", prompt, "--ratio", "9:16"]
    subprocess.run(cmd_img, capture_output=True, text=True, encoding="utf-8")
    time.sleep(1)

    # 2. Send RUN command
    cmd_run = ["node", CLI_PATH, "run"]
    subprocess.run(cmd_run, capture_output=True, text=True, encoding="utf-8")
    time.sleep(1)

    # 3. Trigger Alt+G in Chrome
    ps_cmd = '$wshell = New-Object -ComObject WScript.Shell; $wshell.AppActivate(4952); Start-Sleep -Milliseconds 300; $wshell.SendKeys("%g")'
    subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)

    # 4. Wait up to 35 seconds for new file
    print("Waiting for image to download...")
    start_time = time.time()
    new_file = None

    while time.time() - start_time < 35:
        time.sleep(2)
        after_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.jpeg")))
        diff = after_files - before_files
        if diff:
            new_file = sorted(list(diff), key=os.path.getmtime)[-1]
            break

    if new_file:
        print(f"✓ Downloaded: {os.path.basename(new_file)}")
        shutil.copy2(new_file, dest_path)
        print(f"✓ Copied to: {dest_path}")
    else:
        print(f"⚠️ Timeout waiting for {sc_id}. Will continue to next.")

    time.sleep(3)

print("\nFinished sequential TobyFlow generation loop.")
