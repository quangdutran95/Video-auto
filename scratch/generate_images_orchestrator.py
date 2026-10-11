import os
import sys
import time
import subprocess
import shutil
import re

# Configure standard output to use UTF-8 on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Settings
job_id = "2026-07-12_002_t-t-v-t-n-th-ng"
plan_path = f"jobs/{job_id}/source/creative_plan.toml"
output_dir = f"jobs/{job_id}/input/raw_assets/images"
watch_dir = os.path.join(os.path.expanduser("~"), "Downloads", "tobyflow_output", "tobyflow_bot")
cli_path = r"E:\1.1.0_0\telegram-bridge\cli.js"

os.makedirs(output_dir, exist_ok=True)

def get_pending_scenes():
    """Parses creative_plan.toml and returns a dict of {scene_id: prompt}."""
    pending = {}
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        current_scene_id = None
        current_visual = None
        scene_idx = 1
        
        for line in lines:
            line = line.strip()
            if line.startswith("[[scene_intents]]") or line.startswith("[[creative_plan.scene_intents]]"):
                if current_visual:
                    pending[current_scene_id or f"sc_{scene_idx:02d}"] = current_visual
                    scene_idx += 1
                current_scene_id = None
                current_visual = None
            elif "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                if val.startswith('"""') and val.endswith('"""'):
                    val = val[3:-3]
                elif val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                
                if key == "scene_id" or key == "id":
                    current_scene_id = val
                elif key == "visual_intent":
                    current_visual = val
        
        if current_visual:
            pending[current_scene_id or f"sc_{scene_idx:02d}"] = current_visual
    except Exception as e:
        print(f"Error reading plan file: {e}")
        sys.exit(1)
    return pending

def find_matching_scene(filename, pending_scenes):
    base = os.path.splitext(filename)[0]
    base = re.sub(r'^\d{4}-\d{2}-\d{2}_', '', base)
    file_tokens = [w.lower() for w in re.split(r'[^a-zA-Z0-9]', base) if w]
    
    if not file_tokens:
        return None
        
    best_match = None
    best_score = -1.0
    
    for scene_id, prompt in pending_scenes.items():
        prompt_tokens = [w.lower() for w in re.split(r'[^a-zA-Z0-9]', prompt) if w]
        if not prompt_tokens:
            continue
            
        match_count = 0
        max_compare = min(len(file_tokens), len(prompt_tokens))
        
        for i in range(max_compare):
            f_tok = file_tokens[i]
            p_tok = prompt_tokens[i]
            if f_tok == p_tok:
                match_count += 1
            elif p_tok.startswith(f_tok) or f_tok.startswith(p_tok):
                match_count += 0.8
            else:
                break
                
        score = match_count / len(file_tokens) if file_tokens else 0.0
        if score > best_score and (match_count >= 3 or score >= 0.6):
            best_score = score
            best_match = scene_id
            
    return best_match

def scan_and_copy():
    """Scans watch_dir and copies matching images to output_dir."""
    pending_scenes = get_pending_scenes()
    print(f"\n[Scanner] Scanning watch_dir: {watch_dir}")
    files = [os.path.join(watch_dir, f) for f in os.listdir(watch_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    copied = 0
    for file_path in sorted(files, key=os.path.getmtime):
        filename = os.path.basename(file_path)
        if not filename.startswith("2026-07-12"):
            continue
            
        # Check if already copied to avoid recopying
        matched_scene = find_matching_scene(filename, pending_scenes)
        if matched_scene:
            ext = os.path.splitext(filename)[1]
            dest_filename = f"{matched_scene}{ext}"
            dest_path = os.path.join(output_dir, dest_filename)
            
            if not os.path.exists(dest_path):
                print(f"[Scanner] Copying matched: {filename} -> {matched_scene}")
                shutil.copy2(file_path, dest_path)
                copied += 1
    return copied

def stop_extension_tasks():
    print("[Orchestrator] Stopping active extension tasks...")
    subprocess.run(["node", cli_path, "stop"], capture_output=True)

def run_bridge_generation(timeout_sec):
    print(f"\n[Orchestrator] Running tobyflow_bridge with timeout={timeout_sec}s...")
    cmd = [
        ".venv\\Scripts\\python.exe", "-u", "tools/tobyflow_bridge.py",
        "--plan", plan_path,
        "--output-dir", output_dir,
        "--ratio", "9:16",
        "--batch",
        "--timeout", str(timeout_sec)
    ]
    # We want to run synchronously and stream output
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    for line in proc.stdout:
        print(f"  [Bridge] {line.strip()}")
    proc.wait()
    return proc.returncode

def main():
    all_scenes = get_pending_scenes()
    total_scenes = len(all_scenes)
    print(f"[Orchestrator] Target: {total_scenes} scenes.")

    # Check if images are already present before running generation
    scan_and_copy()
    existing_files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    unique_scenes = set(os.path.splitext(f)[0] for f in existing_files)
    if len(unique_scenes) == total_scenes:
        print(f"\n[SUCCESS] All {total_scenes} images are already generated and mapped successfully!")
        sys.exit(0)

    # 1. Run first attempt with 5 minutes (300 seconds) timeout
    print("\n--- Attempt 1: 5-minute wait ---")
    ret = run_bridge_generation(300)
    
    # 2. Check if we have all files
    existing_files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    unique_scenes = set(os.path.splitext(f)[0] for f in existing_files)
    
    if len(unique_scenes) < total_scenes:
        # 3. Wait 2 minutes more
        print(f"\n--- Not finished ({len(unique_scenes)}/{total_scenes}). Waiting 2 minutes (120s) more for late downloads... ---")
        time.sleep(120)
        
        # Scan and copy any images that arrived during the 2 minutes
        scan_and_copy()
        
        existing_files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        unique_scenes = set(os.path.splitext(f)[0] for f in existing_files)
        
    # 4. Retry loop if still not complete
    attempt = 2
    while len(unique_scenes) < total_scenes and attempt <= 4:
        print(f"\n--- Attempt {attempt}: Re-submitting missing scenes ({total_scenes - len(unique_scenes)} left) ---")
        stop_extension_tasks()
        time.sleep(2)
        
        # Run bridge again for missing ones (timeout 120s)
        run_bridge_generation(120)
        scan_and_copy()
        
        existing_files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        unique_scenes = set(os.path.splitext(f)[0] for f in existing_files)
        attempt += 1

    if len(unique_scenes) == total_scenes:
        print(f"\n[SUCCESS] All {total_scenes} images acquired and mapped successfully!")
        sys.exit(0)
    else:
        print(f"\n[FAILURE] Failed to acquire all images. Only got {len(unique_scenes)}/{total_scenes}.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
