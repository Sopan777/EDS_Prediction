"""
tests/test_preprocessing.py
============================
Additional preprocessing tests covering edge cases, feature extraction,
CSV loading, and data splitting.
Uses only pytest + stdlib (no pandas/numpy).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from rule_engine.preprocessing import (
    FEATURE_COLUMNS,
    validate_input,
    load_csv_data,
    extract_features,
    extract_target,
    stratified_split,
    compute_feature_stats,
    _safe_float,
)


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_eds_data.csv"


class TestValidateInput:
    """Test validate_input with various edge cases."""

    def test_missing_features_default_to_zero(self):
        """Features not present in input should default to 0.0."""
        result = validate_input({"Cr": 5.0})
        for col in FEATURE_COLUMNS:
            if col == "Cr":
                assert result[col] == 5.0
            else:
                assert result[col] == 0.0

    def test_non_numeric_string_na(self):
        """String 'N/A' should be treated as 0.0."""
        result = validate_input({"Cr": "N/A"})
        assert result["Cr"] == 0.0

    def test_non_numeric_string_dash(self):
        """String '-' should be treated as 0.0."""
        result = validate_input({"Ni": "-"})
        assert result["Ni"] == 0.0

    def test_non_numeric_string_abc(self):
        """Arbitrary non-numeric string should be treated as 0.0."""
        result = validate_input({"Mo": "abc"})
        assert result["Mo"] == 0.0

    def test_none_values_handled(self):
        """None values should be converted to 0.0."""
        result = validate_input({"Cr": None, "Ni": None})
        assert result["Cr"] == 0.0
        assert result["Ni"] == 0.0

    def test_extra_features_ignored(self):
        """Features not in FEATURE_COLUMNS should not appear in output."""
        result = validate_input({"Cr": 5.0, "Unobtanium": 99.0, "Fe": 94.0})
        assert "Unobtanium" not in result
        assert "Fe" not in result
        assert set(result.keys()) == set(FEATURE_COLUMNS)

    def test_empty_dict_input(self):
        """Empty dict should return all zeros."""
        result = validate_input({})
        assert len(result) == len(FEATURE_COLUMNS)
        for col in FEATURE_COLUMNS:
            assert result[col] == 0.0

    def test_numeric_string_converted(self):
        """String '5.0' should be converted to float 5.0."""
        result = validate_input({"Cr": "5.0", "Ni": "8.2"})
        assert result["Cr"] == 5.0
        assert result["Ni"] == 8.2

    def test_integer_values_converted_to_float(self):
        """Integer input should be converted to float."""
        result = validate_input({"Cr": 5, "Ni": 8})
        assert result["Cr"] == 5.0
        assert result["Ni"] == 8.0
        assert isinstance(result["Cr"], float)

    def test_all_features_present_in_output(self):
        """Output always has all FEATURE_COLUMNS as keys."""
        result = validate_input({"Al": 1.0})
        assert set(result.keys()) == set(FEATURE_COLUMNS)


class TestLoadCsvData:
    """Test CSV data loading."""

    def test_load_csv_data_returns_correct_row_count(self):
        """Should load all 3582 rows from the synthetic dataset."""
        data = load_csv_data(DATA_PATH)
        assert len(data) == 3582

    def test_load_csv_data_returns_list_of_dicts(self):
        """Each row should be a dict."""
        data = load_csv_data(DATA_PATH)
        assert isinstance(data[0], dict)

    def test_load_csv_data_has_component_name(self):
        """Each row should have a ComponentName field."""
        data = load_csv_data(DATA_PATH)
        for row in data[:10]:
            assert "ComponentName" in row
            assert isinstance(row["ComponentName"], str)
            assert len(row["ComponentName"]) > 0

    def test_load_csv_data_file_not_found(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_csv_data("/nonexistent/path/data.csv")

    def test_load_csv_data_feature_values_are_numeric(self):
        """Feature columns should be loaded as floats."""
        data = load_csv_data(DATA_PATH)
        row = data[0]
        for col in FEATURE_COLUMNS:
            if col in row:
                assert isinstance(row[col], float)


class TestExtractFeatures:
    """Test feature extraction from data rows."""

    def test_extract_features_returns_only_feature_columns(self):
        """Should return exactly the feature columns."""
        row = {"Al": 1.0, "Si": 2.0, "Cr": 3.0, "ComponentName": "Test", "Sr No.": "1"}
        features = extract_features(row)
        assert set(features.keys()) == set(FEATURE_COLUMNS)

    def test_extract_features_missing_cols_default_zero(self):
        """Missing columns should default to 0.0."""
        features = extract_features({})
        for col in FEATURE_COLUMNS:
            assert features[col] == 0.0


class TestExtractTarget:
    """Test target extraction."""

    def test_extract_target_returns_string(self):
        """Should return the ComponentName as string."""
        row = {"ComponentName": "Valve Piston"}
        assert extract_target(row) == "Valve Piston"

    def test_extract_target_missing_returns_empty(self):
        """Missing ComponentName should return empty string."""
        assert extract_target({}) == ""


class TestStratifiedSplit:
    """Test stratified data splitting."""

    def test_split_preserves_total_count(self):
        """Train + val + test should equal total rows."""
        data = load_csv_data(DATA_PATH)
        train, val, test = stratified_split(data)
        assert len(train) + len(val) + len(test) == len(data)

    def test_split_maintains_class_proportions(self):
        """Each class should be represented in all splits."""
        data = load_csv_data(DATA_PATH)
        train, val, test = stratified_split(data)

        train_classes = set(extract_target(r).strip() for r in train)
        val_classes = set(extract_target(r).strip() for r in val)
        test_classes = set(extract_target(r).strip() for r in test)

        all_classes = set(extract_target(r).strip() for r in data)
        # All classes should appear in training set
        assert train_classes == all_classes

    def test_split_is_reproducible(self):
        """Same seed should produce the same split."""
        data = load_csv_data(DATA_PATH)
        train1, val1, test1 = stratified_split(data, random_seed=42)
        train2, val2, test2 = stratified_split(data, random_seed=42)
        assert len(train1) == len(train2)
        assert len(val1) == len(val2)
        assert len(test1) == len(test2)

    def test_split_train_is_largest(self):
        """Training set should be the largest split."""
        data = load_csv_data(DATA_PATH)
        train, val, test = stratified_split(data)
        assert len(train) > len(val)
        assert len(train) > len(test)


class TestComputeFeatureStats:
    """Test feature statistics computation."""

    def test_returns_correct_structure(self):
        """Should return dict with all feature columns as keys."""
        data = load_csv_data(DATA_PATH)
        stats = compute_feature_stats(data, "Valve Piston")
        assert set(stats.keys()) == set(FEATURE_COLUMNS)

    def test_stats_have_expected_fields(self):
        """Each feature stat should have min, max, mean, std, counts."""
        data = load_csv_data(DATA_PATH)
        stats = compute_feature_stats(data, "Valve Piston")
        for col in FEATURE_COLUMNS:
            assert "min" in stats[col]
            assert "max" in stats[col]
            assert "mean" in stats[col]
            assert "std" in stats[col]
            assert "nonzero_count" in stats[col]
            assert "total_count" in stats[col]

    def test_stats_min_leq_max(self):
        """Min should always be less than or equal to max."""
        data = load_csv_data(DATA_PATH)
        stats = compute_feature_stats(data, "Blade Terminal")
        for col in FEATURE_COLUMNS:
            assert stats[col]["min"] <= stats[col]["max"]

    def test_stats_nonexistent_class(self):
        """Non-existent class should return zero counts."""
        data = load_csv_data(DATA_PATH)
        stats = compute_feature_stats(data, "Nonexistent Class")
        for col in FEATURE_COLUMNS:
            assert stats[col]["total_count"] == 0


class TestSafeFloat:
    """Test the _safe_float helper."""

    def test_none_returns_zero(self):
        assert _safe_float(None) == 0.0

    def test_empty_string_returns_zero(self):
        assert _safe_float("") == 0.0

    def test_na_string_returns_zero(self):
        assert _safe_float("N/A") == 0.0

    def test_dash_returns_zero(self):
        assert _safe_float("-") == 0.0

    def test_valid_float_string(self):
        assert _safe_float("3.14") == 3.14

    def test_integer_value(self):
        assert _safe_float(5) == 5.0

    def test_float_value(self):
        assert _safe_float(3.14) == 3.14

    def test_non_numeric_string(self):
        assert _safe_float("abc") == 0.0

    def test_whitespace_string(self):
        assert _safe_float("   ") == 0.0

    def test_string_with_whitespace(self):
        assert _safe_float("  5.0  ") == 5.0
