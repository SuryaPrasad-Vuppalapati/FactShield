"""Comprehensive CI validation script for all FactShield Hub artifacts.

Verifies that all 27 generation cache configs, three dataset splits, FaithBench
labels, four result configs, and the trained classifier are present and non-empty
on HuggingFace Hub. Designed to run in GitHub Actions CI.

Usage::

    python scripts/validate_all.py
"""
import os
import sys
import joblib
from dotenv import load_dotenv
from datasets import load_dataset
from huggingface_hub import login, hf_hub_download

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()
login(token=os.environ['HF_TOKEN'])

passed = 0
failed = 0


def check(label, fn):
    """Run a validation function and track pass/fail counts.

    Args:
        label: Human-readable name of the check, printed in the output.
        fn: A zero-argument callable that raises an exception on failure.
    """
    global passed, failed
    try:
        fn()
        print(f"  PASS: {label}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {label} — {e}")
        failed += 1


print("\n=== 1. Dataset splits ===")
for config in ['cnndm_splits', 'xsum_splits', 'faithbench_splits']:
    def _check_split(c=config):
        ds = load_dataset('factshield-team/cache', c)
        assert len(ds['train']) > 0
    check(config, _check_split)

print("\n=== 2. Cache configs (27 total) ===")
for model in ['bart', 't5', 'pegasus']:
    for dataset in ['cnndm', 'xsum', 'faithbench']:
        for suffix in ['summaries', 'k_samples', 'token_scores']:
            config = f'{model}_{dataset}_{suffix}'

            def _check_cache(c=config):
                ds = load_dataset('factshield-team/cache', c)
                assert len(ds['train']) > 0
            check(config, _check_cache)

print("\n=== 3. FaithBench labels ===")


def _check_labels():
    ds = load_dataset('factshield-team/faithbench-labels')['train']
    assert len(ds) == 800


check('faithbench-labels', _check_labels)

print("\n=== 4. Task results ===")
for config in ['task1_scores', 'task2_scores', 'task3_scores', 'final_table']:
    def _check_results(c=config):
        ds = load_dataset('factshield-team/results', c)
        assert len(ds['train']) > 0
    check(config, _check_results)

print("\n=== 5. Trained classifier ===")


def _check_classifier():
    path = hf_hub_download(
        repo_id='factshield-team/fs_models',
        filename='task3_classifier.pkl'
    )
    clf = joblib.load(path)
    assert hasattr(clf, 'predict')


check('task3_classifier.pkl', _check_classifier)

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("All validation checks passed.")
else:
    print(f"{failed} checks failed — review above.")
print('=' * 40)
