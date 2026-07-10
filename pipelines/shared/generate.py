"""Summarization cache generation utilities (Phase 2 - Kaggle T4 GPU).

Provides three generation functions that produce output caches for BART, T5,
and PEGASUS models, pushed to HuggingFace Hub:

- ``generate_summaries``: beam-search summaries (num_beams=4)
- ``generate_k_samples``: K stochastic samples (temperature=1.0)
- ``generate_with_scores``: greedy decoding with token log-probabilities
"""
import torch
from datasets import Dataset
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODELS = {
    'bart': 'facebook/bart-base',
    't5': 'google/t5-small',
    'pegasus': 'google/pegasus-large',
}

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {DEVICE}")


def load_model(name):
    """Load and return a summarization model and its tokenizer.

    Args:
        name: Model key, one of 'bart', 't5', 'pegasus'.

    Returns:
        A tuple of (model, tokenizer) placed on the appropriate device.
    """
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODELS[name], torch_dtype=torch.float16
    ).eval().to(DEVICE)
    tokenizer = AutoTokenizer.from_pretrained(MODELS[name])
    return model, tokenizer


def generate_summaries(model, tokenizer, dataset, model_name, dataset_name):
    """Generate beam-search summaries and push them to HuggingFace Hub.

    Args:
        model: The loaded summarization model.
        tokenizer: The corresponding tokenizer.
        dataset: An iterable of dataset samples.
        model_name: Model label used in the Hub config name.
        dataset_name: Dataset label used in the Hub config name.
    """
    results = []
    for i, sample in enumerate(dataset):
        article_key = 'article' if 'article' in sample else 'document'
        id_key = 'id' if 'id' in sample else 'doc_id'
        inputs = tokenizer(
            sample[article_key], return_tensors='pt',
            truncation=True, max_length=512
        ).to(DEVICE)
        with torch.no_grad():
            out = model.generate(
                **inputs, num_beams=4,
                max_new_tokens=128, no_repeat_ngram_size=3
            )
        summary = tokenizer.decode(out[0], skip_special_tokens=True)
        results.append({
            'doc_id': str(sample[id_key]),
            'source_text': sample[article_key],
            'summary': summary,
        })
        if i % 100 == 0 and i > 0:
            Dataset.from_list(results).push_to_hub(
                'factshield-team/cache',
                config_name=f'{model_name}_{dataset_name}_summaries',
                private=True
            )
            print(f"  checkpoint @ {i}")
    Dataset.from_list(results).push_to_hub(
        'factshield-team/cache',
        config_name=f'{model_name}_{dataset_name}_summaries',
        private=True
    )
    print(f"✓ {model_name}_{dataset_name}_summaries pushed ({len(results)} docs)")


def generate_k_samples(model, tokenizer, dataset, model_name, dataset_name, K=10):
    """Generate K stochastic samples per document and push to HuggingFace Hub.

    Args:
        model: The loaded summarization model.
        tokenizer: The corresponding tokenizer.
        dataset: An iterable of dataset samples.
        model_name: Model label used in the Hub config name.
        dataset_name: Dataset label used in the Hub config name.
        K: Number of stochastic samples to generate per document.
    """
    results = []
    for i, sample in enumerate(dataset):
        article_key = 'article' if 'article' in sample else 'document'
        id_key = 'id' if 'id' in sample else 'doc_id'
        inputs = tokenizer(
            sample[article_key], return_tensors='pt',
            truncation=True, max_length=512
        ).to(DEVICE)
        samples = []
        for _ in range(K):
            with torch.no_grad():
                out = model.generate(
                    **inputs, do_sample=True,
                    temperature=1.0, max_new_tokens=128
                )
            samples.append(tokenizer.decode(out[0], skip_special_tokens=True))
        row = {'doc_id': str(sample[id_key])}
        for k, s in enumerate(samples):
            row[f'summary_k{k + 1}'] = s
        results.append(row)
        if i % 100 == 0 and i > 0:
            Dataset.from_list(results).push_to_hub(
                'factshield-team/cache',
                config_name=f'{model_name}_{dataset_name}_k_samples',
                private=True
            )
            print(f"  checkpoint @ {i}")
    Dataset.from_list(results).push_to_hub(
        'factshield-team/cache',
        config_name=f'{model_name}_{dataset_name}_k_samples',
        private=True
    )
    print(f"✓ {model_name}_{dataset_name}_k_samples pushed ({len(results)} docs)")


def generate_with_scores(model, tokenizer, dataset, model_name, dataset_name):
    """Generate greedy summaries with per-token log-probabilities for Pipeline 3.

    Token log-probabilities are stored as raw float32 bytes in the cache.

    Args:
        model: The loaded summarization model.
        tokenizer: The corresponding tokenizer.
        dataset: An iterable of dataset samples.
        model_name: Model label used in the Hub config name.
        dataset_name: Dataset label used in the Hub config name.
    """
    results = []
    for i, sample in enumerate(dataset):
        article_key = 'article' if 'article' in sample else 'document'
        id_key = 'id' if 'id' in sample else 'doc_id'
        inputs = tokenizer(
            sample[article_key], return_tensors='pt',
            truncation=True, max_length=512
        ).to(DEVICE)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                output_scores=True,
                return_dict_in_generate=True,
                num_beams=1,
                max_new_tokens=128
            )
        scores = torch.stack(out.scores, dim=1)
        log_probs = scores.log_softmax(-1)
        token_ids = out.sequences[0, 1:]
        chosen_lp = log_probs[0, range(len(token_ids)), token_ids]
        results.append({
            'doc_id': str(sample[id_key]),
            'token_logprobs': chosen_lp.cpu().numpy().tobytes(),
            'seq_len': len(token_ids),
        })
        if i % 100 == 0 and i > 0:
            Dataset.from_list(results).push_to_hub(
                'factshield-team/cache',
                config_name=f'{model_name}_{dataset_name}_token_scores',
                private=True
            )
            print(f"  checkpoint @ {i}")
    Dataset.from_list(results).push_to_hub(
        'factshield-team/cache',
        config_name=f'{model_name}_{dataset_name}_token_scores',
        private=True
    )
    print(f"✓ {model_name}_{dataset_name}_token_scores pushed ({len(results)} docs)")
