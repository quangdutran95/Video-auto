#!/usr/bin/env python3
import os
import re
import sys
import argparse
from pathlib import Path

# Try importing toml/tomllib/tomli
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

def clean(word):
    # Remove punctuation and lower for matching
    return re.sub(r"[^\w]", "", word.lower())

def fallback_toml_load(file_path):
    data = {"words": [], "metadata": {}}
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    current_section = None
    current_word = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[[words]]"):
            if current_word:
                data["words"].append(current_word)
                current_word = {}
            current_section = "words"
        elif line.startswith("[metadata]"):
            current_section = "metadata"
        elif "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if current_section == "words":
                if key in ["start", "end", "confidence"]:
                    current_word[key] = float(val)
                else:
                    current_word[key] = val
            elif current_section == "metadata":
                if key == "duration_seconds":
                    data["metadata"][key] = float(val)
                else:
                    data["metadata"][key] = val
    if current_word:
        data["words"].append(current_word)
    return data

def load_toml(file_path):
    if toml_loader:
        with open(file_path, "rb") as f:
            return toml_loader(f)
    else:
        return fallback_toml_load(file_path)

def dump_toml(metadata, sentences, words, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        # Write metadata
        f.write("[metadata]\n")
        f.write(f'audio_path = "{metadata.get("audio_path", "").replace("\\\\", "/").replace("\\", "/")}"\n')
        f.write(f'language = "{metadata.get("language", "vi")}"\n')
        f.write(f'duration_seconds = {metadata.get("duration_seconds", 0.0):.3f}\n')
        f.write(f'model = "{metadata.get("model", "whisper-1")}"\n')
        # Escape newlines in script text
        escaped_text = metadata.get("text", "").replace("\n", "\\n").replace('"', '\\"')
        f.write(f'text = "{escaped_text}"\n\n')
        
        # Write sentences
        for s in sentences:
            f.write("[[sentences]]\n")
            f.write(f'id = "{s["id"]}"\n')
            f.write(f'start = {s["start"]:.3f}\n')
            f.write(f'end = {s["end"]:.3f}\n')
            escaped_s = s["sentence"].replace('"', '\\"')
            f.write(f'sentence = "{escaped_s}"\n')
            word_ids_str = ", ".join(f'"{wid}"' for wid in s["word_ids"])
            f.write(f'word_ids = [{word_ids_str}]\n\n')
            
        # Write words
        for w in words:
            f.write("[[words]]\n")
            f.write(f'id = "{w["id"]}"\n')
            escaped_w = w["word"].replace('"', '\\"')
            f.write(f'word = "{escaped_w}"\n')
            f.write(f'start = {w["start"]:.3f}\n')
            f.write(f'end = {w["end"]:.3f}\n')
            f.write(f'sentence_id = "{w["sentence_id"]}"\n')
            f.write(f'confidence = {w.get("confidence", 1.0):.3f}\n\n')

def align_sequences(orig_words, whisper_words):
    n = len(orig_words)
    m = len(whisper_words)
    
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]
    
    for i in range(1, n + 1):
        dp[i][0] = i * -2
        bt[i][0] = 1 # UP
    for j in range(1, m + 1):
        dp[0][j] = j * -2
        bt[0][j] = 2 # LEFT
        
    for i in range(1, n + 1):
        w_orig = clean(orig_words[i-1])
        for j in range(1, m + 1):
            w_whisp = clean(whisper_words[j-1].get('word') or whisper_words[j-1].get('text') or '')
            
            if w_orig == w_whisp:
                score = 2
            elif w_orig in w_whisp or w_whisp in w_orig:
                score = 1
            else:
                score = -1
                
            match = dp[i-1][j-1] + score
            delete = dp[i-1][j] - 2
            insert = dp[i][j-1] - 2
            
            best = max(match, delete, insert)
            dp[i][j] = best
            
            if best == match:
                bt[i][j] = 0
            elif best == delete:
                bt[i][j] = 1
            else:
                bt[i][j] = 2
                
    i, j = n, m
    alignment = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and bt[i][j] == 0:
            alignment.append((i-1, j-1))
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or bt[i][j] == 1):
            alignment.append((i-1, None))
            i -= 1
        else:
            alignment.append((None, j-1))
            j -= 1
            
    alignment.reverse()
    return alignment

def main():
    parser = argparse.ArgumentParser(description="Align correct script text with Whisper word timestamps.")
    parser.add_argument("--script", required=True, help="Path to script.txt")
    parser.add_argument("--transcript", required=True, help="Path to raw transcript_word_level.toml")
    parser.add_argument("--output", required=True, help="Path to write aligned transcript_word_level.toml")
    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"Error: Script file not found: {args.script}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.transcript):
        print(f"Error: Transcript file not found: {args.transcript}", file=sys.stderr)
        sys.exit(1)

    # Read original script
    with open(args.script, "r", encoding="utf-8") as f:
        script_text = f.read()
    
    # Load transcript data
    data = load_toml(args.transcript)
    whisper_words = data.get("words") or []
    metadata = data.get("metadata") or {}

    # Get lines of original script
    lines = [line.strip() for line in script_text.split("\n") if line.strip()]
    orig_words = []
    for line in lines:
        orig_words.extend(line.split())

    print(f"Aligning {len(orig_words)} script words with {len(whisper_words)} Whisper words...")
    alignment = align_sequences(orig_words, whisper_words)

    # Build aligned word list
    aligned_words = []
    for orig_idx, w_idx in alignment:
        if orig_idx is None:
            continue  # Whisper word deleted (not in original script)
        
        orig_word = orig_words[orig_idx]
        if w_idx is not None:
            start = whisper_words[w_idx].get("start")
            end = whisper_words[w_idx].get("end")
            confidence = whisper_words[w_idx].get("confidence", 1.0)
        else:
            start = None
            end = None
            confidence = 1.0
            
        aligned_words.append({
            "word": orig_word,
            "start": start,
            "end": end,
            "confidence": confidence
        })

    # Interpolate None timestamps
    num_words = len(aligned_words)
    for k in range(num_words):
        if aligned_words[k]["start"] is None:
            prev_idx = None
            for p in range(k - 1, -1, -1):
                if aligned_words[p]["end"] is not None:
                    prev_idx = p
                    break
            
            next_idx = None
            for n_idx in range(k + 1, num_words):
                if aligned_words[n_idx]["start"] is not None:
                    next_idx = n_idx
                    break
                    
            t_start = 0.0 if prev_idx is None else aligned_words[prev_idx]["end"]
            t_end = (t_start + 1.0) if next_idx is None else aligned_words[next_idx]["start"]
            
            gap_len = (next_idx if next_idx is not None else num_words) - (prev_idx if prev_idx is not None else -1) - 1
            gap_pos = k - (prev_idx if prev_idx is not None else -1)
            
            step = (t_end - t_start) / (gap_len + 1)
            aligned_words[k]["start"] = round(t_start + (gap_pos - 1) * step, 3)
            aligned_words[k]["end"] = round(t_start + gap_pos * step, 3)

    # Group into sentences based on original script lines
    sentences = []
    word_counter = 0
    
    for line_idx, line in enumerate(lines):
        line_words = line.split()
        n_line_words = len(line_words)
        
        curr_words = aligned_words[word_counter:word_counter + n_line_words]
        word_counter += n_line_words
        
        if not curr_words:
            continue
            
        s_start = curr_words[0]["start"]
        s_end = curr_words[-1]["end"]
        s_id = f"S_{line_idx+1:03d}"
        
        word_ids = []
        for w_in_s_idx, w in enumerate(curr_words):
            global_word_idx = len(word_ids) + sum(len(s["word_ids"]) for s in sentences) + 1
            w_id = f"W_{global_word_idx:04d}"
            w["id"] = w_id
            w["sentence_id"] = s_id
            word_ids.append(w_id)
            
        sentences.append({
            "id": s_id,
            "start": s_start,
            "end": s_end,
            "sentence": line,
            "word_ids": word_ids
        })

    # Prepare words list for output
    output_words = []
    for w in aligned_words:
        output_words.append({
            "id": w["id"],
            "word": w["word"],
            "start": w["start"],
            "end": w["end"],
            "sentence_id": w["sentence_id"],
            "confidence": w.get("confidence", 1.0)
        })

    # Update metadata text with correct original script
    metadata["text"] = script_text

    # Write output TOML
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    dump_toml(metadata, sentences, output_words, args.output)
    print(f"[SUCCESS] Aligned script and saved output to {args.output}")

if __name__ == "__main__":
    main()
