"""Build and upload FaithBench hallucination labels (Phase 1 - Data ingestion).

Maps FaithBench worst-label and best-label annotations to binary integer values
(Unwanted/Questionable → 1, otherwise → 0), validates the resulting dataset,
and pushes 800 labeled rows to the factshield-team/faithbench-labels Hub repo.
"""
import os
import pandas as pd
from dotenv import load_dotenv
from datasets import Dataset
from huggingface_hub import login

load_dotenv()
login(token=os.environ['HF_TOKEN'])

df = pd.read_csv('data/raw/faithbench.csv')
print(f"Columns: {list(df.columns)}")
HALLUCINATED = {'Unwanted', 'Questionable'}

typed_labels = pd.DataFrame({
    'doc_id': df.index.astype(str),
    'source': df['source'],
    'summary': df['summary'],
    'llm': df['LLM'],
    'worst_label': df['worst-label'],
    'best_label': df['best-label'],
    'label_binary_worst': df['worst-label'].map(lambda x: 1 if x in HALLUCINATED else 0),
    'label_binary_best': df['best-label'].map(lambda x: 1 if x == 'Unwanted' else 0),
})

assert typed_labels['doc_id'].notna().all(), "null doc_ids"
assert typed_labels['label_binary_worst'].isin([0, 1]).all(), "invalid worst labels"
assert typed_labels['label_binary_best'].isin([0, 1]).all(), "invalid best labels"
assert len(typed_labels) == 800, f"expected 800, got {len(typed_labels)}"
print("✓ Validation passed")
print(typed_labels['label_binary_worst'].value_counts())

Dataset.from_pandas(typed_labels, preserve_index=False).push_to_hub(
    'factshield-team/faithbench-labels', private=True
)
print("✓ Typed labels pushed to factshield-team/faithbench-labels")
