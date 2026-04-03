"""Tests for ATS URL resolver — TDD for Task 7."""
from unittest.mock import MagicMock
import pytest

from src.applier.url_resolver import ApplyUrlResolver


def _make_page(url="https://example.com/job/123") -> MagicMock:
    page = MagicMock()
    page.url = url
    page.query_selector.return_value = None
    return page


class TestApplyUrlResolver:
    def test_returns_true_when_apply_button_found_and_clicked(self):
        resolver = ApplyUrlResolver()
        page = _make_page()

        btn = MagicMock()
        btn.is_visible.return_value = True
        page.query_selector.return_value = btn

        result = resolver.resolve_apply_page(page, "https://example.com/job/123")
        assert result is True
        page.goto.assert_called_once_with("https://example.com/job/123", wait_until="domcontentloaded")
        btn.click.assert_called_once()

    def test_returns_false_when_no_apply_button(self):
        resolver = ApplyUrlResolver()
        page = _make_page()
        page.query_selector.return_value = None

        result = resolver.resolve_apply_page(page, "https://example.com/job/123")
        assert result is False

    def test_tries_multiple_selectors(self):
        resolver = ApplyUrlResolver()
        page = _make_page()

        call_count = [0]
        apply_now_btn = MagicMock()
        apply_now_btn.is_visible.return_value = True

        def query_selector_side_effect(sel):
            call_count[0] += 1
            # Return None for the first selector, button for "Apply Now"
            if "Apply Now" in sel:
                return apply_now_btn
            return None

        page.query_selector.side_effect = query_selector_side_effect
        result = resolver.resolve_apply_page(page, "https://example.com/job/123")

        assert result is True
        assert call_count[0] > 1  # tried multiple selectors before finding one
        apply_now_btn.click.assert_called_once()

    def test_skips_invisible_buttons(self):
        resolver = ApplyUrlResolver()
        page = _make_page()

        invisible_btn = MagicMock()
        invisible_btn.is_visible.return_value = False

        page.query_selector.return_value = invisible_btn
        result = resolver.resolve_apply_page(page, "https://example.com/job/123")
        assert result is False
        invisible_btn.click.assert_not_called()

    def test_waits_for_load_after_click(self):
        resolver = ApplyUrlResolver()
        page = _make_page()

        btn = MagicMock()
        btn.is_visible.return_value = True
        page.query_selector.return_value = btn

        resolver.resolve_apply_page(page, "https://example.com/job/123")
        page.wait_for_load_state.assert_called_with("domcontentloaded")
