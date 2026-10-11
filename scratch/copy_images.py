import os
import sys
import re
import shutil
from pathlib import Path

# Configure standard output to use UTF-8 on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Paths
job_id = "2026-07-11_002_c-nh-tranh-t-t"
plan_path = f"jobs/{job_id}/source/creative_plan.toml"
output_dir = f"jobs/{job_id}/input/raw_assets/images"
watch_dir = os.path.join(os.path.expanduser("~"), "Downloads", "tobyflow_output", "tobyflow_bot")

os.makedirs(output_dir, exist_ok=True)

# Parse creative_plan.toml using fallback line parser
pending_scenes = {}
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
                pending_scenes[current_scene_id or f"sc_{scene_idx:02d}"] = current_visual
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
        pending_scenes[current_scene_id or f"sc_{scene_idx:02d}"] = current_visual
except Exception as e:
    print(f"Error reading plan file: {e}")
    exit(1)

print("Pending scenes:")
for sc_id, pr in pending_scenes.items():
    print(f"  {sc_id}: {pr[:50]}...")

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

# Scan watch_dir
print(f"\nScanning watch_dir: {watch_dir}")
files = [os.path.join(watch_dir, f) for f in os.listdir(watch_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

copied = 0
for file_path in sorted(files, key=os.path.getmtime):
    filename = os.path.basename(file_path)
    if not filename.startswith("2026-07-11"):
        continue
        
    matched_scene = find_matching_scene(filename, pending_scenes)
    if matched_scene:
        ext = os.path.splitext(filename)[1]
        dest_filename = f"{matched_scene}{ext}"
        dest_path = os.path.join(output_dir, dest_filename)
        
        print(f"[OK] Matched: {filename} -> {matched_scene}")
        shutil.copy2(file_path, dest_path)
        print(f"  Copied to: {dest_path}")
        copied += 1

print(f"\nDone! Copied {copied} images.")
if copied < len(pending_scenes):
    print("Warning: Some scenes did not get matched.")
