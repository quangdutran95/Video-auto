import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="VieNeu-TTS v1 Speech Generator (Local Merged Model)")
    parser.add_argument("--text", type=str, help="Text to synthesize")
    parser.add_argument("--text-file", type=str, help="Path to text file containing script")
    parser.add_argument("--output", type=str, required=True, help="Path to save output wav file")
    parser.add_argument(
        "--model-path", 
        type=str, 
        default=r"E:\VieNeu-TTS-v1\finetune\output\VieNeu-TTS-0.3B-Merged-NgocDung",
        help="Path to local merged model folder"
    )
    args = parser.parse_args()

    text_content = ""
    if args.text:
        text_content = args.text
    elif args.text_file:
        if not os.path.exists(args.text_file):
            print(f"Error: Text file not found at {args.text_file}", file=sys.stderr)
            sys.exit(1)
        with open(args.text_file, "r", encoding="utf-8") as f:
            text_content = f.read()
    else:
        print("Error: Must provide either --text or --text-file", file=sys.stderr)
        sys.exit(1)

    text_content = text_content.strip()
    if not text_content:
        print("Error: Text is empty", file=sys.stderr)
        sys.exit(1)

    print(f"Loading VieNeu-TTS SDK and initializing standard engine...")
    try:
        from vieneu import Vieneu
    except ImportError:
        print("Error: vieneu library not installed in this Python environment.", file=sys.stderr)
        sys.exit(1)

    try:
        # Pre-emptive GPU memory cleanup
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        tts = Vieneu(
            mode="standard",
            backbone_repo=args.model_path,
            backbone_device="cpu"  # Run on CPU to avoid GPU VRAM limits
        )
        print("[SUCCESS] Model loaded successfully!")
        
        import re
        import numpy as np

        def split_text_by_length(text, max_len=150):
            # Split by punctuation first
            parts = re.split(r'([.\n!?]+)', text)
            chunks = []
            current_chunk = ""
            for part in parts:
                if re.match(r'[.,\n!?]+', part):
                    current_chunk += part
                    # If this chunk exceeds max_len, split it by space
                    if len(current_chunk.strip()) > max_len:
                        words = current_chunk.strip().split()
                        temp = ""
                        for w in words:
                            if len(temp + " " + w) > max_len:
                                if temp.strip():
                                    chunks.append(temp.strip())
                                temp = w
                            else:
                                temp += " " + w
                        if temp.strip():
                            current_chunk = temp
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = ""
                else:
                    current_chunk += part
            if current_chunk.strip():
                # Process the remainder
                words = current_chunk.strip().split()
                temp = ""
                for w in words:
                    if len(temp + " " + w) > max_len:
                        if temp.strip():
                            chunks.append(temp.strip())
                        temp = w
                    else:
                        temp += " " + w
                if temp.strip():
                    chunks.append(temp.strip())
            return [c for c in chunks if c]

        sentences = split_text_by_length(text_content, max_len=150)

        print(f"Divided text into {len(sentences)} natural sentences for CPU generation.")
        all_audios = []
        for i, sentence in enumerate(sentences):
            print(f"Synthesizing sentence {i+1}/{len(sentences)} (len={len(sentence)})...")
            
            # Explicit cleanup
            gc.collect()
            
            # Use top_k=1 (Greedy search) on CPU to avoid torch.topk bad allocation crash
            # Use custom silence and crossfade for seamless concatenation
            part_audio = tts.infer(
                text=sentence, 
                max_chars=256, 
                top_k=1, 
                silence_p=0.2, 
                crossfade_p=0.05
            )
            
            all_audios.append(part_audio)
            
        # Concatenate all generated audio arrays
        audio = np.concatenate(all_audios)
        
        output_dir = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(output_dir, exist_ok=True)
        
        tts.save(audio, args.output)
        print(f"[SUCCESS] Speech generated and saved to: {args.output}")
        
        tts.close()
    except Exception as e:
        print(f"Error during speech synthesis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
