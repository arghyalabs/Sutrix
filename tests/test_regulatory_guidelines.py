import pytest
from backend.core.ecotox.guideline_detector import GuidelineDetector

def test_oecd_guideline_detection():
    # Test direct OECD numbers
    res = GuidelineDetector.detect_guideline("OECD 201")
    assert res["guideline"] == "OECD 201"
    assert res["framework"] == "OECD"
    assert res["confidence"] >= 0.9

    res = GuidelineDetector.detect_guideline("oecd 203 fish acute toxicity")
    assert res["guideline"] == "OECD 203"
    assert res["framework"] == "OECD"
    assert res["confidence"] >= 0.9

    # Test names mapped to guidelines
    res = GuidelineDetector.detect_guideline("algae growth inhibition assay")
    assert res["guideline"] == "OECD 201"
    assert res["framework"] == "OECD"

    res = GuidelineDetector.detect_guideline("ready biodegradability test")
    assert res["guideline"] == "OECD 301"
    assert res["framework"] == "OECD"

def test_epa_reach_framework_detection():
    # Test US EPA aliases
    res = GuidelineDetector.detect_guideline("EPA OPPTS study")
    assert res["guideline"] == "OPPTS"
    assert res["framework"] == "US EPA"
    assert res["confidence"] >= 0.85

    res = GuidelineDetector.detect_guideline("toxcast screening assay")
    assert res["guideline"] == "TOXCAST"
    assert res["framework"] == "US EPA"
    assert res["confidence"] >= 0.85

    # Test ECHA/REACH
    res = GuidelineDetector.detect_guideline("reach ecotox submission")
    assert res["guideline"] == "REACH"
    assert res["framework"] == "ECHA / REACH"
    assert res["confidence"] >= 0.85

    res = GuidelineDetector.detect_guideline("iuclid template")
    assert res["guideline"] == "IUCLID"
    assert res["framework"] == "ECHA / REACH"
    assert res["confidence"] >= 0.85

def test_guideline_non_matches():
    res = GuidelineDetector.detect_guideline("random scientific header")
    assert res["guideline"] is None
    assert res["framework"] is None
    assert res["confidence"] == 0.0
