"""Logistic regression hallucination classifier for Pipeline 3.

Trains a calibrated logistic regression on the five token probability features,
performs cross-validated C-hyperparameter search, and provides push/load helpers
for the HuggingFace Hub model registry."""

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold, cross_val_score
from huggingface_hub import HfApi

FEATURE_COLS = [
    'perplexity', 'mean_entropy', 'max_entropy',
    'tail_mean_nll', 'sent_length'
]


def train(train_df: pd.DataFrame, val_df: pd.DataFrame) -> CalibratedClassifierCV:
    """Train a calibrated logistic regression classifier.

    Performs a cross-validated grid search over L2 regularization strength C
    on train_df, then fits and calibrates the best model on val_df.

    Args:
        train_df: DataFrame with FEATURE_COLS and 'label_binary_worst' column.
        val_df: DataFrame used for calibration with the same schema.

    Returns:
        A fitted CalibratedClassifierCV instance.
    """
    X_train = train_df[FEATURE_COLS].values
    y_train = train_df['label_binary_worst'].values
    X_val = val_df[FEATURE_COLS].values
    y_val = val_df['label_binary_worst'].values

    best_C, best_auroc = 1.0, 0.0
    for C in [0.01, 0.1, 1.0, 10.0]:
        clf = LogisticRegression(C=C, penalty='l2', max_iter=1000)
        cv = cross_val_score(
            clf, X_train, y_train,
            cv=StratifiedKFold(5), scoring='roc_auc'
        )
        print(f"  C={C:.2f} → AUROC {cv.mean():.4f} ± {cv.std():.4f}")
        if cv.mean() > best_auroc:
            best_auroc, best_C = cv.mean(), C

    print(f"✓ Best C={best_C}, val AUROC={best_auroc:.4f}")
    final = LogisticRegression(C=best_C, penalty='l2', max_iter=1000)
    final.fit(X_train, y_train)

    calibrated = CalibratedClassifierCV(final, method='sigmoid', cv='prefit')
    calibrated.fit(X_val, y_val)
    return calibrated


def push_model(clf, token: str):
    """Serialize and push the trained classifier to HuggingFace Hub.

    Args:
        clf: A fitted sklearn-compatible classifier.
        token: HuggingFace API token with write access to factshield-team/fs_models.
    """
    joblib.dump(clf, 'task3_classifier.pkl')
    HfApi().upload_file(
        path_or_fileobj='task3_classifier.pkl',
        path_in_repo='task3_classifier.pkl',
        repo_id='factshield-team/fs_models',
        repo_type='model',
        token=token
    )
    print("✓ Classifier pushed to factshield-team/fs_models")


def load_model_from_hub():
    """Download and deserialize the classifier from HuggingFace Hub.

    Returns:
        The loaded sklearn-compatible classifier.
    """
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id='factshield-team/fs_models',
        filename='task3_classifier.pkl'
    )
    return joblib.load(path)
