import os
os.environ["SAFETENSORS_NO_MMAP"] = "1"

import sys
import traceback

print("Starting debug script with SAFETENSORS_NO_MMAP=1...")
try:
    print("Importing transformers...")
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    print("Transformers imported.")
    
    model_path = r"E:\VieNeu-TTS-v1\finetune\output\VieNeu-TTS-0.3B-Merged-NgocDung"
    
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    print("Tokenizer loaded successfully.")
    
    print("Loading model on cpu...")
    model = AutoModelForCausalLM.from_pretrained(model_path)
    print("Model loaded successfully on CPU!")
except BaseException as e:
    print("An exception occurred:")
    traceback.print_exc()
    sys.exit(99)
