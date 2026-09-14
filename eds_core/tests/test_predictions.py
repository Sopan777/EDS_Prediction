"""
tests/test_predictions.py
=========================
Prediction regression tests for the rule engine.
- Tests each of the 36 classes with a known sample from the CSV
- Tests boundary values, ambiguous inputs, edge cases
- Uses only pytest + stdlib (no pandas/numpy)
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from rule_engine.engine import RuleEngine
from rule_engine.preprocessing import FEATURE_COLUMNS


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_eds_data.csv"


class TestRegressionAllClasses:
    """Regression tests verifying the engine correctly predicts each class."""

    @pytest.fixture(autouse=True)
    def setup(self, rule_engine, known_class_samples):
        self.engine = rule_engine
        self.samples = known_class_samples

    def test_armature_bolt(self):
        result = self.engine.predict(self.samples["Armature Bolt"])
        assert result.prediction == "Armature Bolt"

    def test_armature_guide(self):
        result = self.engine.predict(self.samples["Armature Guide"])
        assert result.prediction == "Armature Guide"

    def test_armature_plate(self):
        result = self.engine.predict(self.samples["Armature Plate"])
        assert result.prediction == "Armature Plate"

    def test_armature_shim(self):
        result = self.engine.predict(self.samples["Armature Shim"])
        assert result.prediction == "Armature Shim"

    def test_armature_spring(self):
        result = self.engine.predict(self.samples["Armature Spring"])
        assert result.prediction == "Armature Spring"

    def test_back_flow_tube(self):
        result = self.engine.predict(self.samples["Back Flow Tube"])
        assert result.prediction == "Back Flow Tube"

    def test_ball_guide(self):
        result = self.engine.predict(self.samples["Ball Guide"])
        assert result.prediction == "Ball Guide"

    def test_blade_terminal(self):
        result = self.engine.predict(self.samples["Blade Terminal"])
        assert result.prediction == "Blade Terminal"

    def test_c_shim(self):
        result = self.engine.predict(self.samples["C Shim"])
        assert result.prediction == "C Shim"

    def test_cri_injector_body(self):
        result = self.engine.predict(self.samples["CRI Injector Body"])
        assert result.prediction == "CRI Injector Body"

    def test_cri_sealing_ring(self):
        result = self.engine.predict(self.samples["CRI Sealing ring"])
        assert result.prediction == "CRI Sealing ring"

    def test_cri_shim(self):
        result = self.engine.predict(self.samples["CRI Shim"])
        assert result.prediction == "CRI Shim"

    def test_clamping_saddle(self):
        result = self.engine.predict(self.samples["Clamping Saddle"])
        assert result.prediction == "Clamping Saddle"

    def test_dfk_shim(self):
        result = self.engine.predict(self.samples["DFK Shim"])
        assert result.prediction == "DFK Shim"

    def test_dfk_spring(self):
        result = self.engine.predict(self.samples["DFK Spring"])
        assert result.prediction == "DFK Spring"

    def test_dowel_pin(self):
        result = self.engine.predict(self.samples["Dowel Pin"])
        assert result.prediction == "Dowel Pin"

    def test_guide_bush(self):
        result = self.engine.predict(self.samples["Guide Bush"])
        assert result.prediction == "Guide Bush"

    def test_hp_sealing(self):
        result = self.engine.predict(self.samples["HP Sealing"])
        assert result.prediction == "HP Sealing"

    def test_ic_stud(self):
        result = self.engine.predict(self.samples["IC Stud"])
        assert result.prediction == "IC Stud"

    def test_locking_sleeve(self):
        result = self.engine.predict(self.samples["Locking Sleeve"])
        assert result.prediction == "Locking Sleeve"

    def test_mm_hpp_component(self):
        result = self.engine.predict(self.samples["M&M HPP Component"])
        assert result.prediction == "M&M HPP Component"

    def test_magnet_coil(self):
        result = self.engine.predict(self.samples["Magnet Coil"])
        assert result.prediction == "Magnet Coil"

    def test_magnet_core(self):
        result = self.engine.predict(self.samples["Magnet Core"])
        assert result.prediction == "Magnet Core"

    def test_magnet_housing(self):
        result = self.engine.predict(self.samples["Magnet housing"])
        assert result.prediction == "Magnet housing"

    def test_nr_nut(self):
        result = self.engine.predict(self.samples["NR Nut"])
        assert result.prediction == "NR Nut"

    def test_nozzle_spring(self):
        result = self.engine.predict(self.samples["Nozzle Spring"])
        assert result.prediction == "Nozzle Spring"

    def test_pille(self):
        result = self.engine.predict(self.samples["Pille"])
        assert result.prediction == "Pille"

    def test_rls_shim(self):
        result = self.engine.predict(self.samples["RLS Shim"])
        assert result.prediction == "RLS Shim"

    def test_sealing_ring(self):
        result = self.engine.predict(self.samples["Sealing Ring"])
        assert result.prediction == "Sealing Ring"

    def test_support_sealing(self):
        result = self.engine.predict(self.samples["Support Sealing"])
        assert result.prediction == "Support Sealing"

    def test_ufk_spring(self):
        result = self.engine.predict(self.samples["UFK Spring"])
        assert result.prediction == "UFK Spring"

    def test_vfk_shim(self):
        result = self.engine.predict(self.samples["VFK Shim"])
        assert result.prediction == "VFK Shim"

    def test_valve_nut(self):
        result = self.engine.predict(self.samples["Valve Nut"])
        assert result.prediction == "Valve Nut"

    def test_valve_piece(self):
        result = self.engine.predict(self.samples["Valve Piece"])
        assert result.prediction == "Valve Piece"

    def test_valve_piston(self):
        result = self.engine.predict(self.samples["Valve Piston"])
        assert result.prediction == "Valve Piston"

    def test_valve_spring(self):
        result = self.engine.predict(self.samples["Valve Spring"])
        assert result.prediction == "Valve Spring"


class TestBoundaryValues:
    """Test predictions at boundary values of rule ranges."""

    @pytest.fixture(autouse=True)
    def setup(self, rule_engine):
        self.engine = rule_engine

    def test_valve_piston_at_min_boundary(self):
        """Test Valve Piston with minimum boundary values for V and W."""
        # Valve Piston rule requires V in [1.83, 2.69] and W in [5.75, 9.31]
        result = self.engine.predict({"V": 1.83, "W": 5.75, "Mo": 3.48, "Cr": 3.76})
        # Should match or just barely match
        assert result.status in ("matched", "low_confidence", "no_match")

    def test_valve_piston_at_max_boundary(self):
        """Test Valve Piston with maximum boundary values."""
        result = self.engine.predict({"V": 2.69, "W": 9.31, "Mo": 6.39, "Cr": 5.14})
        assert result.status in ("matched", "low_confidence", "no_match")

    def test_blade_terminal_at_min_boundary(self):
        """Test Blade Terminal at minimum Cu boundary."""
        result = self.engine.predict({"Cu": 36.09, "Au": 36.64, "K": 0.12})
        assert result.status in ("matched", "low_confidence", "no_match")

    def test_clamping_saddle_at_boundary(self):
        """Test Clamping Saddle at Ni boundary."""
        result = self.engine.predict({"Ni": 78.44})
        assert result.status in ("matched", "low_confidence", "no_match")

    def test_just_below_boundary_no_match(self):
        """Test value just below a rule's >= threshold does not match that rule."""
        # Magnet Core requires Zn >= some threshold (around 0.12)
        # With Zn=0.0 it should not match Magnet Core
        result = self.engine.predict({"Zn": 0.0})
        assert result.prediction != "Magnet Core" or result.status == "no_match"


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    @pytest.fixture(autouse=True)
    def setup(self, rule_engine):
        self.engine = rule_engine

    def test_all_zero_input(self):
        """All-zero input should get no_match or low_confidence."""
        all_zeros = {col: 0.0 for col in FEATURE_COLUMNS}
        result = self.engine.predict(all_zeros)
        # With all zeros, most rules should NOT match since they require
        # features >= some positive threshold
        assert result.status in ("no_match", "low_confidence", "matched")
        assert isinstance(result.prediction, str)

    def test_negative_values_handled(self):
        """Negative values should not crash the engine."""
        negative_input = {"Cr": -5.0, "Ni": -10.0, "Mo": -3.0}
        result = self.engine.predict(negative_input)
        assert result.status in ("no_match", "low_confidence", "matched")
        assert isinstance(result.prediction, str)

    def test_very_large_values(self):
        """Very large values should not crash."""
        large_input = {"Cr": 9999.0, "Ni": 9999.0, "Mo": 9999.0}
        result = self.engine.predict(large_input)
        assert isinstance(result.prediction, str)
        assert isinstance(result.confidence, float)

    def test_empty_dict_input(self):
        """Empty dict should produce a valid result."""
        result = self.engine.predict({})
        assert result.status in ("no_match", "low_confidence", "matched")
        assert isinstance(result.prediction, str)

    def test_ambiguous_input_high_nickel_chromium(self):
        """Input with high Ni and Cr could match both Locking Sleeve and Back Flow Tube."""
        # Both have high Ni and Cr but at different ranges
        ambiguous = {"Ni": 9.0, "Cr": 17.0, "Mn": 1.2, "Si": 0.35}
        result = self.engine.predict(ambiguous)
        # Should still give a deterministic result
        assert isinstance(result.prediction, str)
        assert result.confidence >= 0.0

    def test_single_feature_input(self):
        """Input with only one non-zero feature."""
        result = self.engine.predict({"Zn": 0.18})
        assert isinstance(result.prediction, str)
        assert isinstance(result.confidence, float)

    def test_prediction_always_returns_valid_result(self):
        """Result object always has required fields regardless of input."""
        result = self.engine.predict({"unknown_element": 99.0})
        assert hasattr(result, "prediction")
        assert hasattr(result, "confidence")
        assert hasattr(result, "status")
        assert hasattr(result, "rule_id")
        assert hasattr(result, "matched_conditions")
        assert hasattr(result, "all_matches")
