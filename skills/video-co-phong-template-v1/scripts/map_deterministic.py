#!/usr/bin/env python3
import os
import re
import sys
import argparse
from pathlib import Path

# Try to import tomllib (Python 3.11+) or tomli/toml
toml_loader = None
try:
    import tomllib
    toml_loader = tomllib.load
except ImportError:
    try:
        import toml
        toml_loader = toml.load
    except ImportError:
        try:
            import tomli
            toml_loader = tomli.load
        except ImportError:
            pass

def clean_word(w):
    return re.sub(r"[^\w]", "", w.lower())

def fallback_toml_load(file_path):
    # Simple line-by-line fallback parser if no TOML library is available
    data = {}
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Very simple parser tailored for our metadata and words/scenes list
    current_section = None
    current_item = {}
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
            
        if line.startswith("[[") and line.endswith("]]"):
            sec_name = line[2:-2]
            if current_item:
                data.setdefault(current_section, []).append(current_item)
                current_item = {}
            current_section = sec_name
        elif line.startswith("[") and line.endswith("]"):
            sec_name = line[1:-1]
            current_section = sec_name
            data[current_section] = {}
        elif "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            
            # parse basic types
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            else:
                try:
                    if "." in val:
                        val = float(val)
                    else:
                        val = int(val)
                except ValueError:
                    pass
            
            if current_section in ["words", "scene_intents"]:
                current_item[key] = val
            elif isinstance(data.get(current_section), dict):
                data[current_section][key] = val
                
    if current_item:
        data.setdefault(current_section, []).append(current_item)
        
    return data

def load_toml(file_path):
    if toml_loader:
        with open(file_path, "rb") as f:
            return toml_loader(f)
    else:
        return fallback_toml_load(file_path)

def dump_mappings_toml(mappings, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        for m in mappings:
            f.write("[[mappings]]\n")
            f.write(f'id = "{m["id"]}"\n')
            f.write(f'scene_id = "{m["scene_id"]}"\n')
            f.write(f'subdivision_role = "{m["subdivision_role"]}"\n')
            f.write(f'subdivision_index = {m["subdivision_index"]}\n')
            f.write(f'subdivision_total = {m["subdivision_total"]}\n')
            f.write(f'asset_id = "{m["asset_id"]}"\n')
            f.write(f'asset_scene_id = "{m["asset_scene_id"]}"\n')
            f.write(f'start = {m["start"]:.3f}\n')
            f.write(f'end = {m["end"]:.3f}\n')
            f.write(f'file_path = "{m["file_path"]}"\n')
            f.write(f'source_start = {m["source_start"]:.3f}\n')
            f.write(f'source_end = {m["source_end"]:.3f}\n')
            f.write(f'fit_score = {m["fit_score"]:.3f}\n')
            # format lists to valid TOML
            labels_str = ", ".join(f'"{l}"' for l in m["fit_labels"])
            f.write(f'fit_labels = [{labels_str}]\n')
            f.write(f'reason = "{m["reason"]}"\n')
            f.write(f'fallback = {str(m["fallback"]).lower()}\n')
            f.write(f'warnings = []\n\n')

def main():
    parser = argparse.ArgumentParser(description="Deterministic asset mapper for TobyFlow template.")
    parser.add_argument("--creative-plan", type=str, required=True, help="Path to creative_plan.toml")
    parser.add_argument("--transcript", type=str, required=True, help="Path to transcript_word_level.toml")
    parser.add_argument("--output", type=str, required=True, help="Path to save semantic_mapping.toml")
    parser.add_argument("--image-dir", type=str, help="Optional image directory path to verify files exist")
    args = parser.parse_args()

    if not os.path.exists(args.creative_plan):
        print(f"Error: Creative plan not found at {args.creative_plan}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.transcript):
        print(f"Error: Transcript not found at {args.transcript}", file=sys.stderr)
        sys.exit(1)

    # Load TOMLs using standard loader or custom fallback
    creative = load_toml(args.creative_plan)
    transcript = load_toml(args.transcript)

    scenes = creative.get("scene_intents") or []
    words = transcript.get("words") or []
    
    # Metadata duration parsing
    metadata = transcript.get("metadata") or {}
    total_duration = float(metadata.get("duration_seconds") or 0.0)

    if not scenes:
        print("Error: No scene intents found in creative plan.", file=sys.stderr)
        sys.exit(1)
    if not words:
        print("Error: No words found in transcript.", file=sys.stderr)
        sys.exit(1)

    print(f"Aligning {len(scenes)} scenes with {len(words)} transcript words...")

    # Calculate word counts for each scene spoken_text
    scene_word_counts = []
    for s in scenes:
        spoken = s.get("spoken_text") or ""
        cleaned = [clean_word(w) for w in spoken.split() if clean_word(w)]
        scene_word_counts.append(len(cleaned))

    mappings = []
    word_idx = 0

    # Get job root directory context to construct file paths relatively
    job_dir_path = Path(args.output).parents[1]
    job_rel_dir = os.path.relpath(job_dir_path, start=os.getcwd()).replace("\\", "/")

    for idx, (scene, count) in enumerate(zip(scenes, scene_word_counts)):
        scene_id = scene.get("id") or f"sc_{idx+1:02d}"
        
        # Slice transcript words
        scene_words = words[word_idx:word_idx + count]
        
        if not scene_words:
            start_time = mappings[-1]["end"] if mappings else 0.0
            end_time = start_time + 5.0
        else:
            start_time = float(scene_words[0]["start"])
            end_time = float(scene_words[-1]["end"])
            
        word_idx += count
        
        # Map 1-to-1 to corresponding sc_XX.jpeg
        image_name = f"{scene_id}.jpeg"
        file_path = f"{job_rel_dir}/input/raw_assets/images/{image_name}"
        
        mappings.append({
            "id": f"MAP_{idx+1:03d}",
            "scene_id": scene_id,
            "subdivision_role": "primary",
            "subdivision_index": 1,
            "subdivision_total": 1,
            "asset_id": f"AST_{idx+1:03d}",
            "asset_scene_id": f"AST_{idx+1:03d}_SC_01",
            "start": start_time,
            "end": end_time,
            "file_path": file_path,
            "source_start": 0.0,
            "source_end": 0.0,
            "fit_score": 1.0,
            "fit_labels": ["deterministic-1to1"],
            "reason": f"Khớp nối 1-đối-1 chính xác ảnh sinh {image_name} cho phân cảnh {scene_id} theo quy trình TobyFlow.",
            "fallback": False
        })

    # Snapping logic: prevent gaps between clips
    for idx in range(len(mappings)):
        if idx > 0:
            mappings[idx]["start"] = mappings[idx-1]["end"]

    # Extend last mapping to the end of the voiceover
    if mappings and total_duration > 0:
        mappings[-1]["end"] = total_duration

    # Output TOML
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    dump_mappings_toml(mappings, args.output)
        
    print(f"[SUCCESS] Snapped and mapped {len(mappings)} scenes deterministically to {args.output}")

if __name__ == "__main__":
    main()
