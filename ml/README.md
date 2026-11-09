# SentimentIQ ML component

This Python package is the ML boundary shared with the FastAPI platform. It stays independent of FastAPI and SQLAlchemy. The v1 runnable baseline uses VADER plus a small explicit aspect lexicon; it is not a trained or calibrated domain model.

## Install for local development

From the repository root:

```powershell
python -m pip install -e .\ml
```

FastAPI imports `sentimentiq_ml`. Its lifespan should call `get_model_info(domain)` once per worker, which initializes and retains the default engine. Run CPU-bound batch inference outside the async event loop. The platform owns retries and persistence.

## Public API

```python
from sentimentiq_ml import analyze, analyze_batch, compute_analytics, get_model_info

get_model_info(domain) -> ModelInfo
analyze(text, domain) -> AnalysisResult
analyze_batch(texts, domain) -> list[BatchOutcome]
compute_analytics(results) -> AnalyticsSummary
```

- Domains: `product`, `campus`.
- Labels: `positive`, `negative`, `neutral`, `mixed`.
- Sentiment score: polarity in `[-1.0, 1.0]`; the label is a separate classification.
- Confidence: `[0.0, 1.0]`, with kind `raw_score` initially. Use `calibrated_probability` only after calibration and evaluation.
- Aspect offsets: nullable pair, zero-based and end-exclusive Unicode code-point offsets into the original input text.
- Each batch call returns one ordered `BatchOutcome` per input. Exactly one of `result` and `error` is populated. The platform maps `input_index` to a dataset row and owns retries and failed-attempt storage.
- Model identity is one `model_id` and immutable `model_revision` per job.
- Analytics consumes successful persisted results. Sentiment percentages use successful results as the denominator. Confidence aggregates are grouped by kind and include counts.

## Baseline limitations

The baseline identifies aspects only from a maintained domain vocabulary, so unseen aspect terms are omitted. `mixed` is a rule-based label when contrastive clauses receive opposing sentiment labels. The `raw_score` comes from VADER's normalized lexicon scores and is not calibrated. Amazon star ratings provide weak positive/neutral/negative labels only; they do not provide ground truth for `mixed` or aspect sentiment. Campus performance needs a labeled campus feedback set for meaningful evaluation.

## Dataset preparation

The `prepare_amazon` module converts a downloaded Amazon Reviews JSONL/JSONL.GZ file into text, label, and product-group columns while omitting user IDs. Labels map 1-2 stars to negative, 2.5-3.5 to neutral, and 4-5 to positive. This mapping is weak supervision; do not treat it as human sentiment annotation. A `--limit` export is only an early-record development sample and may be biased. Keep source data and generated files under ignored `ml/data/` and do not commit them.

UCSD/McAuley Lab's Amazon Reviews 2023 data is one possible product-review source. Check its terms and intended use before using or redistributing it. The VADER library and source lexicon are MIT licensed.

## Optional product model training

Install the training dependencies with `python -m pip install -e ".[training]"` from `ml/`. Prepare a permitted Amazon sample, then run:

```powershell
python -m sentimentiq_ml.prepare_amazon .\data\reviews.jsonl.gz .\data\reviews.csv
python -m sentimentiq_ml.train_model .\data\reviews.csv --preflight-only --test-size 0.2
python -m sentimentiq_ml.train_model .\data\reviews.csv .\artifacts\product-model.joblib .\artifacts\evaluation.json
```

The preflight command does not fit a model. It reports row and distinct product-group counts for each sentiment label in both the 80% training partition and 20% holdout. It checks for at least 100 distinct product groups per label in the holdout and exits with code 2 if any label is below that minimum. Training enforces the same check. The trainer and preflight use the same deterministic split procedure. If sampling, sample across product groups rather than taking the first N records.

Set `SENTIMENTIQ_MODEL_PATH` to the resulting artifact before starting a worker. The trained TF-IDF/logistic-regression model is used for the `product` domain; `campus` stays on VADER. The command creates a product-group holdout report. Its `predict_proba` outputs remain `raw_score` values and are not calibrated probabilities. Do not load joblib artifacts from untrusted sources. Keep datasets, model artifacts, and reports out of Git.
