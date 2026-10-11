import os
import sys
import time
import argparse
import subprocess
import shutil
import re
from pathlib import Path

# Configure standard output to use UTF-8 on Windows to avoid charmap encode errors
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


# Try importing toml or tomli for parsing creative_plan.toml
try:
    import toml
except ImportError:
    # Fallback to standard library parsing if not available
    toml = None

def parse_creative_plan(plan_path):
    """Parses creative_plan.toml and extracts prompts with scene IDs."""
    if not os.path.exists(plan_path):
        print(f"Error: Creative plan file not found at {plan_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing creative plan from: {plan_path}")
    prompts = []
    use_toml = toml is not None
    if use_toml:
        try:
            data = toml.load(plan_path)
            # Support both flat list or nested structure
            scenes = data.get("scene_intents") or data.get("creative_plan", {}).get("scene_intents", [])
            for idx, scene in enumerate(scenes):
                scene_id = scene.get("scene_id") or scene.get("id") or f"sc_{idx+1:02d}"
                visual_intent = scene.get("visual_intent")
                if visual_intent:
                    prompts.append((scene_id, visual_intent))
        except Exception as e:
            print(f"Warning: Failed to parse TOML using library: {e}. Falling back to line parser.", file=sys.stderr)
            use_toml = False

    if not use_toml:
        # Simple line-by-line fallback parser for TOML
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
                        prompts.append((current_scene_id or f"sc_{scene_idx:02d}", current_visual))
                        scene_idx += 1
                    current_scene_id = None
                    current_visual = None
                elif "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key == "scene_id" or key == "id":
                        current_scene_id = val
                    elif key == "visual_intent":
                        current_visual = val
            
            if current_visual:
                prompts.append((current_scene_id or f"sc_{scene_idx:02d}", current_visual))
        except Exception as e:
            print(f"Error reading plan file: {e}", file=sys.stderr)
            sys.exit(1)

    return prompts

def get_output_files(watch_dir):
    """Returns a set of all media file paths in the watch directory."""
    files = set()
    if not os.path.exists(watch_dir):
        return files
    
    for entry in os.scandir(watch_dir):
        if entry.is_file() and entry.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.mp4')):
            files.add(entry.path)
    return files

def find_matching_scene(filename, pending_scenes):
    """Matches a filename to a scene ID based on prompt keyword similarity."""
    base = os.path.splitext(filename)[0]
    # Remove date prefix YYYY-MM-DD_
    base = re.sub(r'^\d{4}-\d{2}-\d{2}_', '', base)
    file_tokens = [w.lower() for w in re.split(r'[^a-zA-Z0-9]', base) if w]
    
    if not file_tokens:
        return None
        
    best_match = None
    best_score = -1.0
    
    for scene_id, prompt in pending_scenes.items():
        # Clean prompt
        prompt_tokens = [w.lower() for w in re.split(r'[^a-zA-Z0-9]', prompt) if w]
        if not prompt_tokens:
            continue
            
        # Count how many of the first few file_tokens match the prompt_tokens at the same position
        match_count = 0
        max_compare = min(len(file_tokens), len(prompt_tokens))
        
        for i in range(max_compare):
            f_tok = file_tokens[i]
            p_tok = prompt_tokens[i]
            if f_tok == p_tok:
                match_count += 1
            elif p_tok.startswith(f_tok) or f_tok.startswith(p_tok):
                # partial match (e.g. truncated words)
                match_count += 0.8
            else:
                break
                
        score = match_count / len(file_tokens) if file_tokens else 0.0
        # Require at least 3 matching tokens or a high matching score to avoid false positives
        if score > best_score and (match_count >= 3 or score >= 0.6):
            best_score = score
            best_match = scene_id
            
    return best_match

def main():
    parser = argparse.ArgumentParser(description="TobyFlow Image Generation Bridge")
    parser.add_argument("--plan", type=str, help="Path to creative_plan.toml")
    parser.add_argument("--prompt", type=str, help="Single prompt to generate (for testing)")
    parser.add_argument("--scene-id", type=str, default="test_image", help="Scene ID for single prompt test")
    parser.add_argument("--output-dir", type=str, required=True, help="Directory to save the collected images")
    parser.add_argument("--ratio", type=str, default="9:16", help="Image aspect ratio (default: 9:16)")
    parser.add_argument(
        "--cli-path", 
        type=str, 
        default=r"E:\1.1.0_0\telegram-bridge\cli.js",
        help="Path to TobyFlow cli.js"
    )
    parser.add_argument(
        "--watch-dir", 
        type=str, 
        default=os.path.join(os.path.expanduser("~"), "Downloads", "tobyflow_output", "tobyflow_bot"),
        help="Path to folder where TobyFlow saves generated images"
    )
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds to wait for image(s)")
    parser.add_argument("--batch", action="store_true", help="Enable batch multi-prompt generation mode")
    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.cli_path):
        print(f"Error: TobyFlow cli.js not found at {args.cli_path}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.watch_dir, exist_ok=True)

    # Collect prompts
    prompts = []
    if args.plan:
        prompts = parse_creative_plan(args.plan)
    elif args.prompt:
        prompts = [(args.scene_id, args.prompt)]
    else:
        print("Error: Must specify either --plan or --prompt", file=sys.stderr)
        sys.exit(1)

    if not prompts:
        print("Warning: No visual prompts found to generate.")
        sys.exit(0)

    # Filter out scenes that already have files in output_dir
    todo_prompts = []
    for scene_id, prompt in prompts:
        existing_files = [f for f in os.listdir(args.output_dir) if os.path.splitext(f)[0] == scene_id]
        if existing_files:
            print(f"✓ Scene {scene_id} already exists ({existing_files[0]}). Skipping.")
        else:
            todo_prompts.append((scene_id, prompt))

    if not todo_prompts:
        print("All scenes already have generated images. Nothing to do!")
        sys.exit(0)

    print(f"Starting image generation for {len(todo_prompts)} scenes using TobyFlow...")
    print(f"Watching directory: {args.watch_dir}")

    if args.batch and len(todo_prompts) > 1:
        print(f"\n⚡ Running in BATCH mode (Multi-Prompt queueing) ⚡\n")
        
        # 1. Capture watch directory state before enqueuing
        before_files = get_output_files(args.watch_dir)
        
        # Create map of pending scenes for lookup
        pending_scenes = {scene_id: prompt for scene_id, prompt in todo_prompts}
        total_pending = len(pending_scenes)
        
        # 2. Join all prompts with double newlines and submit once
        joined_prompts = "\n\n".join(prompt for _, prompt in todo_prompts)
        print(f"Submitting batch of {total_pending} prompts to TobyFlow...")
        
        cmd = ["node", args.cli_path, "image", joined_prompts, "--ratio", args.ratio, "--mode", "multi"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
            print(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            print(f"Error calling TobyFlow CLI: {e.stderr}", file=sys.stderr)
            sys.exit(1)
            
        print("\nAll prompts submitted as a single batch to TobyFlow! Waiting for images to download...\n")
        
        # 3. Watch directory loop
        start_time = time.time()
        completed_count = 0
        
        while time.time() - start_time < args.timeout:
            if not pending_scenes:
                break
                
            time.sleep(2)
            after_files = get_output_files(args.watch_dir)
            new_files = after_files - before_files
            
            if new_files:
                for file_path in sorted(list(new_files), key=os.path.getmtime):
                    filename = os.path.basename(file_path)
                    matched_scene = find_matching_scene(filename, pending_scenes)
                    
                    if matched_scene:
                        ext = os.path.splitext(filename)[1]
                        dest_filename = f"{matched_scene}{ext}"
                        dest_path = os.path.join(args.output_dir, dest_filename)
                        
                        print(f"✓ Matched file: {filename} -> {matched_scene}")
                        print(f"  Copying to: {dest_path}")
                        
                        shutil.copy2(file_path, dest_path)
                        # Remove from pending lists
                        pending_scenes.pop(matched_scene)
                        before_files.add(file_path) # Add to before_files so we don't process it again
                        completed_count += 1
                        print(f"  [{completed_count}/{total_pending}] Complete.")
                        
        if pending_scenes:
            print(f"\n❌ Error: Timeout reached. The following {len(pending_scenes)} scenes were not generated/matched:", file=sys.stderr)
            for sc_id, pr in pending_scenes.items():
                print(f"  - {sc_id}: {pr}", file=sys.stderr)
            sys.exit(1)
            
    else:
        # Sequential Mode (Standard)
        for scene_id, prompt in todo_prompts:
            print("\n" + "="*50)
            print(f"Scene: {scene_id} | Prompt: {prompt}")
            print("="*50)

            # 1. Get current files in watch directory
            before_files = get_output_files(args.watch_dir)

            # 2. Call TobyFlow CLI via node
            cmd = ["node", args.cli_path, "image", prompt, "--ratio", args.ratio]
            print(f"Executing: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
                print(result.stdout.strip())
            except subprocess.CalledProcessError as e:
                print(f"Error calling TobyFlow CLI: {e.stderr}", file=sys.stderr)
                sys.exit(1)

            # 3. Wait for new file to appear
            print(f"Waiting for generated image (timeout={args.timeout}s)...")
            img_start_time = time.time()
            new_file_path = None

            while time.time() - img_start_time < args.timeout:
                time.sleep(1)
                after_files = get_output_files(args.watch_dir)
                new_files = after_files - before_files
                
                if new_files:
                    # Get the newest file
                    new_file_path = sorted(list(new_files), key=os.path.getmtime)[-1]
                    break

            if new_file_path:
                ext = os.path.splitext(new_file_path)[1]
                dest_filename = f"{scene_id}{ext}"
                dest_path = os.path.join(args.output_dir, dest_filename)
                
                print(f"✓ Found new file: {new_file_path}")
                print(f"Copying and renaming to: {dest_path}")
                
                # Copy to destination folder
                shutil.copy2(new_file_path, dest_path)
                print(f"✓ Scene {scene_id} completed.")
                print("Sleeping for 10 seconds to allow the extension to cool down...")
                time.sleep(10)
            else:
                print(f"❌ Error: Timeout waiting for image of scene {scene_id}", file=sys.stderr)
                sys.exit(1)

    print("\nAll image generation completed successfully!")

if __name__ == "__main__":
    main()
