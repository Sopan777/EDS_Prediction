# Rule-Based Prediction Engine

## Overview

The rule-based prediction engine is an alternative to the ML model pipeline for EDS
(Energy Dispersive Spectroscopy) component classification. It uses interpretable
range-based rules derived from elemental composition patterns to predict component
classes.

**Key properties:**
- Pure Python stdlib implementation (no pandas, numpy, or scikit-learn required)
- Deterministic predictions with full explainability
- 91%+ test accuracy on the synthetic EDS dataset (36 classes)
- Rules generated automatically from training data
- Versioned rule files for reproducibility

## Architecture

```
rule_engine/
  __init__.py          - Package entry point, exports main classes
  models.py            - Data classes: Rule, RuleSet, RuleMatch, PredictionResult
  preprocessing.py     - CSV loading, feature extraction, input validation
  engine.py            - Production RuleEngine class (load, evaluate, resolve)
  validator.py         - Rule quality checks and coverage statistics
  predictor.py         - Integration layer (matches predictor.py pattern)
  rules/
    rules.json         - Generated rule set (versioned, reproducible)

training/
  __init__.py          - Package entry point
  analyze_dataset.py   - Dataset profiling and analysis
  train_rules.py       - Rule generation from CSV data
  evaluate_rules.py    - Evaluation and baseline comparison
```

## Algorithm

### Why Range-Based Rules?

The EDS dataset has 36 component classes, each with distinctive elemental
composition fingerprints. Many classes are uniquely identifiable by:
- Presence/absence of specific elements (K only in Blade Terminal, Ca only in NR Nut)
- Distinct concentration ranges (high Ni >78 only in Clamping Saddle)
- Combinations of elements at specific levels

Range-based rules are ideal because:
1. They directly encode the domain knowledge (elemental fingerprints)
2. They are fully interpretable (each prediction can be explained)
3. They handle the highly separable class structure efficiently
4. No external dependencies required for inference

### Rule Generation Process

1. **Data Loading**: CSV parsed with stdlib `csv` module
2. **Stratified Split**: 80/10/10 train/validation/test split
3. **Feature Analysis**: Per-class min/max/mean/std computed for each element
4. **Condition Generation**: For each class, identify discriminating features:
   - Features uniquely non-zero for the class (score: 1.0)
   - Features with ranges above or below all other classes (score: 0.95)
   - Features with non-overlapping ranges (score: 0.85)
   - Features with partially separable ranges (score proportional to discrimination)
5. **Validation**: Rules evaluated on validation set for precision/recall
6. **Pruning**: Remove conditions that do not improve precision
7. **Priority Assignment**: Based on validation accuracy + specificity + support
8. **Fallback Generation**: Simpler rules for classes not well covered by primary rules

### Conflict Resolution

When multiple rules match an input, conflicts are resolved deterministically:

1. **Highest validation_accuracy** (primary criterion)
2. **Highest confidence** (first tiebreaker)
3. **Highest support** (second tiebreaker)
4. **Most specific** - more conditions (third tiebreaker)
5. **Alphabetical rule_id** (final deterministic tiebreaker)

## Usage

### Basic Prediction

```python
from rule_engine.engine import RuleEngine

engine = RuleEngine()
result = engine.predict({"Cr": 4.5, "Mo": 5.0, "V": 2.2, "W": 7.5, "Ni": 0.3})

print(result.prediction)    # "Valve Piston"
print(result.confidence)    # 1.0
print(result.status)        # "matched"
print(result.rule_id)       # "rule_valve_piston_primary"
```

### Using the Integration Layer

```python
from rule_engine.predictor import predict_component_rules

result = predict_component_rules({"Pb": 3.0, "Cr": 1.5})
print(result["prediction"])   # "CRI Injector Body"
print(result["explanation"])  # Human-readable explanation
```

### Batch Prediction

```python
from rule_engine.predictor import predict_components_batch_rules

spectra = [
    {"Cr": 4.5, "Mo": 5.0, "V": 2.2, "W": 7.5, "Ni": 0.3},
    {"Pb": 3.0, "Cr": 1.5},
    {"K": 2.0, "Cu": 5.0},
]
results = predict_components_batch_rules(spectra)
```

### Custom Configuration

```python
engine = RuleEngine(
    rules_path="path/to/custom_rules.json",
    confidence_threshold=0.6,  # Stricter threshold
)
```

## Rule Format (rules.json)

```json
{
  "version": "1.0.0",
  "generated_at": "2024-01-01T00:00:00+00:00",
  "dataset_hash": "abc123...",
  "algorithm": "range_based_with_pruning",
  "validation_score": 0.92,
  "rules_count": 36,
  "rules": [
    {
      "id": "rule_valve_piston_primary",
      "conditions": [
        {"feature": "V", "operator": ">=", "threshold": 1.5},
        {"feature": "W", "operator": ">=", "threshold": 5.0}
      ],
      "prediction": "Valve Piston",
      "confidence": 1.0,
      "support": 80,
      "validation_accuracy": 1.0,
      "priority": 950,
      "description": "Range-based rule for Valve Piston (2 conditions)"
    }
  ],
  "metadata": {
    "feature_columns": ["Al", "Si", "P", "S", "Cr", ...],
    "n_classes": 36,
    "classes": ["Armature Bolt", ...],
    "train_size": 2850,
    "test_accuracy": 0.92
  }
}
```

## Regenerating Rules

To regenerate rules from the training data:

```bash
python training/train_rules.py
```

This will:
1. Load `data/synthetic_eds_data.csv`
2. Split into train/validation/test sets (deterministic, seed=42)
3. Generate and validate rules
4. Save rules to `rule_engine/rules/rules.json`
5. Save report to `outputs/rule_generation_report.json`

To evaluate the rule engine:

```bash
python training/evaluate_rules.py
```

To analyze the dataset:

```bash
python training/analyze_dataset.py
```

## Confidence and Fallback Behavior

- **matched** (confidence >= threshold): High-confidence prediction. The rule matched
  and has good validation accuracy.
- **low_confidence** (confidence < threshold, but rule matched): A rule fired but its
  precision during validation was below the configured threshold (default: 0.40).
  Manual review is recommended.
- **no_match**: No rules matched the input composition. The input does not match any
  known component elemental pattern. Returns "Unknown" as the prediction.

## Configuration

Configuration is centralized in `config.py`:

```python
RULE_ENGINE = {
    "RULES_DIR": BASE_DIR / "rule_engine" / "rules",
    "RULES_FILE": BASE_DIR / "rule_engine" / "rules" / "rules.json",
    "RULE_CONFIDENCE_THRESHOLD": 0.40,
    "RULE_MIN_SUPPORT": 3,
    "RULE_ENGINE_VERSION": "1.0.0",
}
```

## Comparison with ML Models

| Aspect | Rule Engine | ML Models (RF, XGBoost, etc.) |
|--------|-------------|-------------------------------|
| Dependencies | Python stdlib only | pandas, numpy, sklearn, etc. |
| Interpretability | Full (rule conditions shown) | Limited (feature importance) |
| Accuracy | ~92% | ~98%+ (with ensemble) |
| Inference speed | Fast (rule matching) | Fast (tree traversal) |
| Training speed | Seconds | Minutes |
| Reproducibility | Deterministic from CSV | Depends on random state |
| Deployment | Single JSON file | Pickle files |

The rule engine trades some accuracy for full interpretability and zero external
dependencies. It is ideal for:
- Environments where installing ML libraries is not possible
- Cases where prediction explanations are required
- Quick prototyping and baseline comparisons
- Edge/embedded deployment with minimal Python installations
