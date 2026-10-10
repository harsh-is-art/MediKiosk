"""
Downloader script for local Qwen-VL model (Qwen/Qwen2-VL-2B-Instruct).
Caches model weights and processor locally for CUDA GPU inference.
"""

import sys
import os

MODEL_ID = os.getenv("QWEN_VL_MODEL", "Qwen/Qwen2-VL-2B-Instruct")

print(f"============================================================")
print(f"  Qwen-VL Local Model Downloader")
print(f"  Target Model: {MODEL_ID}")
print(f"============================================================")

try:
    import torch
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    else:
        print("WARNING: CUDA is not active. For RTX 4060 GPU acceleration, run:")
        print("  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
except ImportError:
    print("ERROR: PyTorch is not installed. Please run:")
    print("  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
    sys.exit(1)

try:
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    from huggingface_hub import snapshot_download

    print(f"\n[1/2] Downloading HuggingFace model files for {MODEL_ID}...")
    snapshot_download(repo_id=MODEL_ID, resume_download=True)
    print("  ✓ Model snapshot downloaded.")

    print(f"\n[2/2] Initializing processor and verifying model loading...")
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )
    print("\n============================================================")
    print("  SUCCESS: Qwen2-VL model downloaded and ready for local OCR!")
    print("============================================================")

except Exception as e:
    print(f"\nERROR downloading Qwen-VL model: {e}")
    print("Ensure you have installed required packages via:")
    print("  pip install transformers qwen-vl-utils paddleocr accelerate huggingface_hub")
    sys.exit(1)
