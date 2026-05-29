import pytest
from backend.core.ecotox.duration_parser import DurationParser

def test_duration_detection():
    # Test standard exact matches
    duration, conf = DurationParser.detect_duration("96h")
    assert duration == "96h"
    assert conf == 1.0

    duration, conf = DurationParser.detect_duration("14d")
    assert duration == "14d"
    assert conf == 1.0

    # Test hour strings
    duration, conf = DurationParser.detect_duration("96-h")
    assert duration == "96h"
    assert conf == 0.85

    duration, conf = DurationParser.detect_duration("48 hours")
    assert duration == "48h"
    assert conf == 0.85

    # Test day strings
    duration, conf = DurationParser.detect_duration("14 days")
    assert duration == "14d"
    assert conf == 0.85

    # Test week/month/year strings
    duration, conf = DurationParser.detect_duration("4 weeks")
    assert duration == "4w"
    assert conf == 0.80

    duration, conf = DurationParser.detect_duration("3 months")
    assert duration == "3mo"
    assert conf == 0.80

    duration, conf = DurationParser.detect_duration("2 years")
    assert duration == "2y"
    assert conf == 0.80

    # Test non-matches
    duration, conf = DurationParser.detect_duration("concentration")
    assert duration == ""
    assert conf == 0.0

def test_duration_normalization():
    # 96h -> 4 days
    res = DurationParser.normalize_duration("96h")
    assert res["value"] == 96.0
    assert res["unit"] == "hours"
    assert res["standardized_days"] == 4.0

    # 14d -> 14 days
    res = DurationParser.normalize_duration("14d")
    assert res["value"] == 14.0
    assert res["unit"] == "days"
    assert res["standardized_days"] == 14.0

    # 4w -> 28 days
    res = DurationParser.normalize_duration("4w")
    assert res["value"] == 4.0
    assert res["unit"] == "weeks"
    assert res["standardized_days"] == 28.0

    # 3mo -> 90 days
    res = DurationParser.normalize_duration("3mo")
    assert res["value"] == 3.0
    assert res["unit"] == "months"
    assert res["standardized_days"] == 90.0

    # 2y -> 730 days
    res = DurationParser.normalize_duration("2y")
    assert res["value"] == 2.0
    assert res["unit"] == "years"
    assert res["standardized_days"] == 730.0

    # lifetime -> -1
    res = DurationParser.normalize_duration("lifetime")
    assert res["value"] == -1.0
    assert res["unit"] == "lifetime"
    assert res["standardized_days"] == -1.0

def test_duration_column_aliases():
    assert DurationParser.is_duration_column("duration") is True
    assert DurationParser.is_duration_column("exposure_duration") is True
    assert DurationParser.is_duration_column("study_length") is True
    assert DurationParser.is_duration_column("smiles") is False
