"""Tests for the intent signal detection module."""

from __future__ import annotations

import pytest

from sahiixx_agency.discovery.intent_signals import (
    IntentSignal,
    SignalTier,
    aggregate_signals,
    detect_signals,
)


class TestDetectSignals:
    """Tests for the detect_signals function."""

    def test_hot_funding_signal(self) -> None:
        text = "Acme Corp raised a Series B of $45M led by Sequoia"
        signals = detect_signals(text, source="news")
        assert len(signals) >= 1
        funding = [s for s in signals if s.signal_type == "funding_round"]
        assert len(funding) == 1
        assert funding[0].tier == SignalTier.HOT
        assert funding[0].confidence > 0

    def test_hot_rfp_signal(self) -> None:
        text = "Government issues RFP for cloud migration project"
        signals = detect_signals(text, source="news")
        rfp = [s for s in signals if s.signal_type == "rfp_published"]
        assert len(rfp) == 1
        assert rfp[0].tier == SignalTier.HOT

    def test_hot_executive_hire_signal(self) -> None:
        text = "TechStartup appoints new CTO from Google"
        signals = detect_signals(text, source="linkedin")
        hire = [s for s in signals if s.signal_type == "executive_hire"]
        assert len(hire) == 1
        assert hire[0].tier == SignalTier.HOT

    def test_warm_digital_transformation_signal(self) -> None:
        text = "Company investing in digital transformation initiative"
        signals = detect_signals(text, source="news")
        dt = [s for s in signals if s.signal_type == "digital_transformation_post"]
        assert len(dt) == 1
        assert dt[0].tier == SignalTier.WARM

    def test_warm_office_expansion_signal(self) -> None:
        text = "Firm opens new office in Dubai, hiring 50 engineers"
        signals = detect_signals(text, source="news")
        expansion = [s for s in signals if s.signal_type == "office_expansion"]
        assert len(expansion) == 1
        assert expansion[0].tier == SignalTier.WARM

    def test_nurture_podcast_signal(self) -> None:
        text = "CEO appeared on the Tech Podcast show discussing AI"
        signals = detect_signals(text, source="news")
        podcast = [s for s in signals if s.signal_type == "podcast_appearance"]
        assert len(podcast) == 1
        assert podcast[0].tier == SignalTier.NURTURE

    def test_gcc_government_tender_signal(self) -> None:
        text = "ADNOC issues tender for digital platform modernization"
        signals = detect_signals(text, source="news", include_gcc=True)
        gcc = [s for s in signals if s.signal_type.startswith("gcc_")]
        assert len(gcc) >= 1
        assert gcc[0].tier == SignalTier.WARM

    def test_gcc_vision_2030_signal(self) -> None:
        text = "NEOM project seeks technology partners for Vision 2030"
        signals = detect_signals(text, source="news", include_gcc=True)
        vision = [s for s in signals if s.signal_type == "gcc_vision_2030_project"]
        assert len(vision) == 1

    def test_no_signals_for_irrelevant_text(self) -> None:
        text = "The weather is nice today and I had a good lunch"
        signals = detect_signals(text, source="news")
        assert len(signals) == 0

    def test_multiple_signals_detected(self) -> None:
        text = "Startup raised $10M Series A and appoints new CTO, opening London office"
        signals = detect_signals(text, source="news")
        signal_types = {s.signal_type for s in signals}
        assert "funding_round" in signal_types
        assert "executive_hire" in signal_types

    def test_gcc_disabled(self) -> None:
        text = "ADNOC issues tender for platform"
        signals = detect_signals(text, source="news", include_gcc=False)
        gcc = [s for s in signals if s.signal_type.startswith("gcc_")]
        assert len(gcc) == 0

    def test_outreach_angle_populated(self) -> None:
        text = "Company raised a Series A round"
        signals = detect_signals(text, source="news")
        assert len(signals) >= 1
        for signal in signals:
            assert signal.outreach_angle != ""


class TestAggregateSignals:
    """Tests for the aggregate_signals function."""

    def test_aggregate_hot_signal(self) -> None:
        signals = [
            IntentSignal(
                signal_type="funding_round",
                tier=SignalTier.HOT,
                source="news",
                confidence=0.8,
            )
        ]
        result = aggregate_signals("TestCo", signals)
        assert result.entity_name == "TestCo"
        assert result.overall_tier == SignalTier.HOT
        assert result.score > 0
        assert len(result.signals) == 1

    def test_aggregate_empty_signals(self) -> None:
        result = aggregate_signals("TestCo", [])
        assert result.entity_name == "TestCo"
        assert result.overall_tier == SignalTier.NURTURE
        assert result.score == 0.0

    def test_aggregate_mixed_tiers(self) -> None:
        signals = [
            IntentSignal(
                signal_type="funding_round",
                tier=SignalTier.HOT,
                source="news",
                confidence=0.9,
            ),
            IntentSignal(
                signal_type="digital_transformation_post",
                tier=SignalTier.WARM,
                source="linkedin",
                confidence=0.7,
            ),
        ]
        result = aggregate_signals("TestCo", signals)
        assert result.overall_tier == SignalTier.HOT  # Hot takes precedence
        assert result.score > 0

    def test_aggregate_score_calculation(self) -> None:
        signals = [
            IntentSignal(
                signal_type="funding_round",
                tier=SignalTier.HOT,
                source="news",
                confidence=1.0,
            )
        ]
        result = aggregate_signals("TestCo", signals)
        # HOT weight (3.0) * confidence (1.0) = 3.0
        assert result.score == pytest.approx(3.0)
