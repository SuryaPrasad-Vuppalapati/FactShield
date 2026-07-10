"""Data download script (Phase 1 - Data ingestion).

Downloads CNN/DailyMail, XSum, and FaithBench datasets and saves them
to the local data/raw/ directory. Run once before splitting.
"""
import os
import pandas as pd
from dotenv import load_dotenv
from datasets import load_dataset
from huggingface_hub import login

load_dotenv()
login(token=os.environ['HF_TOKEN'])

os.makedirs('data/raw', exist_ok=True)

cnndm = load_dataset('cnn_dailymail', '3.0.0')
cnndm.save_to_disk('data/raw/cnndm')
print(f"✓ CNN/DailyMail: {cnndm}")

xsum = load_dataset('EdinburghNLP/xsum')
xsum.save_to_disk('data/raw/xsum')
print(f"✓ XSUM: {xsum}")

faithbench_url = 'https://raw.githubusercontent.com/vectara/FaithBench/main/FaithBench.csv'
faithbench = pd.read_csv(faithbench_url)
faithbench.to_csv('data/raw/faithbench.csv', index=False)
print(f"✓ FaithBench: {faithbench.shape}")
