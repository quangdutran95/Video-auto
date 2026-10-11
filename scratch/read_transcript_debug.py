import json

path = r"C:\Users\Home\.gemini\antigravity-ide\brain\3359bae6-b1d3-4e25-9a3a-b0cae88b984c\.system_generated\logs\transcript.jsonl"
out_path = r"e:\Video-Auto\scratch\read_transcript_debug.txt"
with open(path, "r", encoding="utf-8") as f, open(out_path, "w", encoding="utf-8") as out:
    for line in f:
        item = json.loads(line)
        idx = item.get("step_index", 0)
        if 325 <= idx <= 345:
            out.write(f"=== STEP {idx} ===\n")
            out.write(item.get("content", "") + "\n")
            if "tool_calls" in item:
                out.write(f"Tool calls: {json.dumps(item['tool_calls'], indent=2)}\n")
print("Done writing to scratch/read_transcript_debug.txt")
