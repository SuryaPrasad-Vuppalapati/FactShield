"""CLI runner for the entailment scoring pipeline (Pipeline 2).

Reads a YAML config or CLI arguments to determine which model/dataset/methods to
run, executes the scoring pipeline, deduplicates against any existing results on
HuggingFace Hub, and pushes the updated task2_scores dataset.

Usage::

    python -m pipelines.entailment.run --model_name bart --dataset cnndm --methods minicheck
    python -m pipelines.entailment.run --config configs/entailment.yaml
"""
import argparse
import yaml
import os
import pandas as pd
from dotenv import load_dotenv
from datasets import load_dataset, Dataset
from huggingface_hub import login
from pipelines.entailment.pipeline import run_pipeline

load_dotenv()
login(token=os.environ['HF_TOKEN'])


def main():
    """Parse arguments, run the entailment pipeline, and push results to HuggingFace Hub."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=False)
    parser.add_argument('--model_name', default=None)
    parser.add_argument('--dataset', default=None)
    parser.add_argument('--methods', default=None, nargs='+')
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = {
            'model_name': args.model_name,
            'dataset': args.dataset,
            'methods': args.methods or ['minicheck'],
        }

    results, elapsed = run_pipeline(
        model_name=cfg['model_name'],
        dataset_name=cfg['dataset'],
        methods=cfg.get('methods', ['minicheck'])
    )

    df = pd.DataFrame(results)
    df['latency_ms'] = (elapsed * 1000) / len(df['doc_id'].unique())
    df['split'] = 'test'

    # Append to existing instead of overwriting
    try:
        existing = load_dataset('factshield-team/results', 'task2_scores')['train'].to_pandas()
        df = pd.concat([existing, df], ignore_index=True).drop_duplicates(
            subset=['doc_id', 'summarizer', 'dataset', 'method']
        )
        print(f"  appended, total rows now: {len(df)}")
    except Exception as e:
        print(f"  first run, creating fresh ({e})")

    Dataset.from_pandas(df, preserve_index=False).push_to_hub(
        'factshield-team/results',
        config_name='task2_scores',
        private=True
    )
    print(f"✓ task2_scores pushed ({cfg['model_name']} × {cfg['dataset']})")


if __name__ == '__main__':
    main()
