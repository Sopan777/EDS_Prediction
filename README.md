# EDS Extraction + Component Prediction Pipeline

Combines the EDS/EDAX PDF/DOCX table extractor with the component-prediction
models from `EDS_Component_Prediction_v2.ipynb` into one pipeline:

```
report.pdf/.docx --> eds_extractor --> spectra --> predictor --> component predictions
```

## Project layout

```
eds_pipeline/
├── config.py               # all paths / constants / defaults in one place
├── data_utils.py            # data loading + preprocessing (notebook §1-4)
├── noise.py                  # Gaussian noise injection, on/off toggle
├── models/
│   ├── base_model.py         # shared interface every model implements
│   ├── random_forest_model.py   # <- one file per model, as requested
│   ├── extra_trees_model.py
│   ├── catboost_model.py
│   └── xgboost_model.py
├── model_registry.py         # maps "random_forest"/"catboost"/... -> model class
├── train_all_models.py       # FULL notebook pipeline (§1-15) as a script
├── predictor.py               # inference: load model, predict, noise toggle
├── eds_pipeline.py             # combined extractor + predictor CLI
├── compare_models.py            # run every model side-by-side, print comparison
├── eds_extractor.py              # (unchanged) PDF/EDS table extraction
├── docx_to_pdf.py                 # (unchanged) DOCX -> PDF conversion
├── data/synthetic_eds_data.csv     # training data
├── saved_models/                    # trained .pkl files land here
└── outputs/                          # plots / saved JSON land here
```

## Setup

```bash
pip install -r requirements.txt
```

CatBoost and XGBoost are optional. If either isn't installed, `model_registry.py`
prints a notice and simply skips that model everywhere (training, prediction,
comparison) — the rest of the pipeline still works with whatever models ARE
available.

## 1. Train all models

Runs the entire notebook end-to-end: data checks, class-separability check,
5-fold stratified CV comparison, final model training, the noise-robustness
stress test, classification report, confusion matrices, feature importance,
and saving every model + the label encoder + feature list + the
most-noise-robust model's name.

```bash
python train_all_models.py
python train_all_models.py --data path/to/other_data.xlsx
python train_all_models.py --no-plots      # skip saving PNGs to outputs/
```

You can also train just one model (handy while iterating on hyperparameters
for a single algorithm) by running its file directly:

```bash
python models/random_forest_model.py
python models/catboost_model.py
```

## 2. Run the combined extraction + prediction pipeline

Extracts every EDS table from a report and predicts the component for
**every spectrum found** (handles multiple spectra, and multiple tables,
automatically):

```bash
python eds_pipeline.py report.pdf
python eds_pipeline.py report.docx
```

Options:

| Flag | Meaning |
|---|---|
| `--model {random_forest,extra_trees,catboost,xgboost}` | which trained model to use (default: the most noise-robust one chosen during training) |
| `--noise` / `--no-noise` | turn simulated measurement-noise injection on/off before predicting (default: off) |
| `--noise-level FLOAT` | noise magnitude relative to each element's training std, e.g. `0.25` (only applies when `--noise` is set) |
| `--top-k INT` | how many candidate components to return per spectrum (default 3) |
| `--confidence-threshold FLOAT` | below this probability, flagged "Unknown / needs review" (default 0.40) |
| `--save-json PATH` | save the full extraction + predictions as JSON |

```bash
python eds_pipeline.py report.pdf --model catboost --noise --noise-level 0.25 --save-json outputs/report_predictions.json
```

## 3. Compare all models on the same spectra

Runs **every** trained model against the same spectrum/spectra and prints
their predictions side by side — top prediction, confidence, whether models
agree, and the full top-k ranking per model.

Two input modes:

```bash
# From a report - extracts every spectrum and compares all models on each one
python compare_models.py report.pdf

# From hand-built spectra (JSON list of {element: value} dicts, or
# {"label": ..., "values": {...}} dicts) - useful for specific test cases
python compare_models.py spectra.json
```

Options: same `--noise` / `--no-noise` / `--noise-level` / `--top-k` /
`--confidence-threshold` / `--save-json` as above, plus `--models` to compare
only a subset (e.g. `--models random_forest catboost`).

The same noisy version of each spectrum is used for every model in a given
comparison run, so the comparison stays apples-to-apples.

## Using `predictor.py` directly in code

```python
import predictor

result = predictor.predict_component(
    {"C": 0.2, "O": 0.1, "Fe": 76.0, "Cr": 12.5, "Ni": 8.2, ...},
    model_key="catboost",      # or None for the default (most noise-robust) model
    top_k=3,
    noise_enabled=True,        # the on/off toggle
    noise_level=0.25,
)
print(result)                   # DataFrame: Component, Probability
if "flag" in result.attrs:
    print(result.attrs["flag"])  # "LOW CONFIDENCE — treat as Unknown / needs manual review"
```

`predictor.predict_components_batch([...])` does the same for a list of
spectra in one call — this is what `eds_pipeline.py` uses internally to
handle multiple spectra from one report.

## Notes / caveats carried over from the notebook

- The noise-robustness ranking is based on **simulated** Gaussian noise
  scaled to each element's within-class training std. It's a reasonable
  proxy for instrument noise / calibration drift, not a guarantee of
  real-world behavior — re-run `train_all_models.py` against real noisy
  measurements when available.
- Tree-based `feature_importances_` (impurity-based) can be misleading for
  correlated features (several elements co-vary within an alloy family).
  Cross-check with permutation importance or SHAP if this is going to drive
  a real decision (e.g. dropping elements to speed up measurement).
- Predictions below `--confidence-threshold` are flagged rather than
  silently returned as a top-3 guess.
