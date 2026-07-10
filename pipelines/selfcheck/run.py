"""CLI runner for the SelfCheckGPT consistency scoring pipeline (Pipeline 1).

Runs the selfcheck scoring pipeline for a given model/dataset pair and pushes
the sentence-level results as task1_scores to HuggingFace Hub.

Usage::

    python -m pipelines.selfcheck.run --model_name bart --dataset cnndm --K 5 --score_mode nli
    python -m pipelines.selfcheck.run --config configs/selfcheck.yaml
"""
import argparse
import yaml
import os
import pandas as pd
from dotenv import load_dotenv
from datasets import load_dataset, Dataset
from huggingface_hub import login
from pipelines.selfcheck.pipeline import run_pipeline

load_dotenv()
login(token=os.environ['HF_TOKEN'])


def main():
    """Parse arguments, run the SelfCheckGPT pipeline, and push results to HuggingFace Hub."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=False)
    parser.add_argument('--model_name', default=None)
    parser.add_argument('--dataset', default=None)
    parser.add_argument('--K', type=int, default=5)
    parser.add_argument('--score_mode', default='all')
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = {
            'model_name': args.model_name,
            'dataset': args.dataset,
            'K': args.K,
            'score_mode': args.score_mode,
        }

    model_name = cfg['model_name']
    dataset_name = cfg['dataset']
    K = cfg.get('K', 5)
    score_mode = cfg.get('score_mode', 'all')

    results, elapsed = run_pipeline(model_name, dataset_name, K, score_mode)

    df = pd.DataFrame(results)
    df['latency_ms'] = (elapsed * 1000) / len(df['doc_id'].unique())
    df['split'] = 'test'

    try:
        existing = load_dataset('factshield-team/results', 'task1_scores')['train'].to_pandas()
        df = pd.concat([existing, df], ignore_index=True).drop_duplicates(
            subset=['doc_id', 'summarizer', 'dataset', 'score_mode']
        )
        print(f"  appended, total rows now: {len(df)}")
    except Exception as e:
        print(f"  first run, creating fresh ({e})")

    Dataset.from_pandas(df, preserve_index=False).push_to_hub(
        'factshield-team/results',
        config_name='task1_scores',
        private=True
    )
    print(f"task1_scores pushed ({model_name} × {dataset_name})")


if __name__ == '__main__':
    main()
