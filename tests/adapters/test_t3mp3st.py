"""Tests for the T3MP3ST security adapter."""

from __future__ import annotations

from sahiixx_agency.adapters.security._t3mp3st_validation import validate_target


def test_validate_target_accepts_public_host():
    assert validate_target("example.com") is None


def test_validate_target_rejects_localhost():
    assert validate_target("localhost") == "blocked_target"


def test_validate_target_rejects_private_ip():
    assert validate_target("192.168.1.1") == "blocked_target"


def test_validate_target_allows_local_when_configured():
    assert validate_target("localhost", allow_local=True) is None


def test_validate_target_rejects_empty():
    assert validate_target("") == "missing_target"


def test_validate_target_accepts_url():
    assert validate_target("https://example.com/path") is None
