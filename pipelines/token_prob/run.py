"""CLI runner for the token probability pipeline (Pipeline 3).

Runs feature extraction, trains the logistic regression classifier on
FaithBench-labeled data, pushes the model to HuggingFace Hub, and uploads
task3_scores results.

Usage::

    python -m pipelines.token_prob.run --model_name bart --dataset cnndm
    python -m pipelines.token_prob.run --config configs/token_prob.yaml
"""
import argparse
import yaml
import os
import pandas as pd
from dotenv import load_dotenv
from datasets import load_dataset, Dataset
from huggingface_hub import login
from pipelines.token_prob.pipeline import run_pipeline
from pipelines.token_prob.classifier import train, push_model

load_dotenv()
login(token=os.environ['HF_TOKEN'])


def main():
    """Parse arguments, run feature extraction + classifier training, and push results."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=False)
    parser.add_argument('--model_name', default=None)
    parser.add_argument('--dataset', default=None)
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = {
            'model_name': args.model_name,
            'dataset': args.dataset,
        }

    model_name = cfg['model_name']
    dataset_name = cfg['dataset']

    merged, elapsed = run_pipeline(model_name, dataset_name)

    merged_labeled = merged.dropna(subset=['label_binary_worst'])

    FEATURE_COLS = ['perplexity', 'mean_entropy', 'max_entropy',
                    'tail_mean_nll', 'sent_length']

    if len(merged_labeled) == 0:
        print(f"⚠ No labels found for {model_name} × {dataset_name}, skipping classifier training")
        test_df = merged.copy()
        test_df['score'] = float('nan')
        test_df['split'] = 'test'
        test_df['method'] = 'token_prob_classifier'
        test_df['latency_ms'] = (elapsed * 1000) / len(test_df)
    else:
        train_df = merged_labeled.sample(frac=0.70, random_state=42)
        val_df = merged_labeled.drop(train_df.index).sample(frac=0.50, random_state=42)

        clf = train(train_df, val_df)
        push_model(clf, token=os.environ['HF_TOKEN'])

        test_df = merged.copy()
        test_df['score'] = clf.predict_proba(test_df[FEATURE_COLS].values)[:, 1]
        test_df['split'] = 'test'
        test_df['method'] = 'token_prob_classifier'
        test_df['latency_ms'] = (elapsed * 1000) / len(test_df)

    try:
        existing = load_dataset('factshield-team/results', 'task3_scores')['train'].to_pandas()
        test_df = pd.concat([existing, test_df], ignore_index=True).drop_duplicates(
            subset=['doc_id', 'summarizer', 'dataset']
        )
        print(f"  appended, total rows now: {len(test_df)}")
    except Exception as e:
        print(f"  first run, creating fresh ({e})")

    Dataset.from_pandas(test_df, preserve_index=False).push_to_hub(
        'factshield-team/results',
        config_name='task3_scores',
        private=True
    )
    print(f"✓ task3_scores pushed ({model_name} × {dataset_name})")


if __name__ == '__main__':
    main()
