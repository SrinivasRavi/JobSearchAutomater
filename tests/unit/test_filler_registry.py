"""Tests for BaseFormFiller interface and filler registry — TDD for Task 3."""
import pytest

from src.applier.base import BaseFormFiller, FillResult
from src.applier.registry import get_filler_for_url, register_filler
from src.models.user_profile import UserProfile


def _make_profile() -> UserProfile:
    return UserProfile(
        profile_id="test",
        profile_name="test",
        first_name="John",
        last_name="Doe",
        full_name="John Doe",
        email="john@example.com",
        phone="+1-555-0000",
        city="NYC",
        state="NY",
        country="USA",
        zip_code="10001",
    )


class FakeWorkdayFiller(BaseFormFiller):
    def platform_name(self) -> str:
        return "workday"

    def can_handle(self, url: str) -> bool:
        return "myworkdayjobs.com" in url or "workday.com" in url

    def fill_form(self, page) -> FillResult:
        return FillResult(success=True, fields_filled=["name", "email"], fields_skipped=[])

    def submit(self, page) -> bool:
        return True


class FakeOracleHCMFiller(BaseFormFiller):
    def platform_name(self) -> str:
        return "oracle_hcm"

    def can_handle(self, url: str) -> bool:
        return "taleo.net" in url or "oraclecloud.com" in url

    def fill_form(self, page) -> FillResult:
        return FillResult(success=True, fields_filled=["name"], fields_skipped=["phone"])

    def submit(self, page) -> bool:
        return True


class TestFillResult:
    def test_success_result(self):
        r = FillResult(success=True, fields_filled=["name", "email"], fields_skipped=[])
        assert r.success is True
        assert "name" in r.fields_filled
        assert r.error == ""

    def test_failure_result(self):
        r = FillResult(success=False, fields_filled=[], fields_skipped=["name"], error="Timeout")
        assert r.success is False
        assert r.error == "Timeout"


class TestBaseFormFiller:
    def test_instantiation_with_profile(self):
        profile = _make_profile()
        filler = FakeWorkdayFiller(profile)
        assert filler.profile is profile

    def test_platform_name(self):
        filler = FakeWorkdayFiller(_make_profile())
        assert filler.platform_name() == "workday"

    def test_can_handle_matching_url(self):
        filler = FakeWorkdayFiller(_make_profile())
        assert filler.can_handle("https://nasdaq.wd1.myworkdayjobs.com/apply")

    def test_can_handle_non_matching_url(self):
        filler = FakeWorkdayFiller(_make_profile())
        assert not filler.can_handle("https://greenhouse.io/apply")

    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            BaseFormFiller(_make_profile())  # type: ignore


class TestFillerRegistry:
    def setup_method(self):
        """Register fakes before each test."""
        register_filler(FakeWorkdayFiller)
        register_filler(FakeOracleHCMFiller)

    def test_returns_correct_filler_for_workday_url(self):
        profile = _make_profile()
        filler = get_filler_for_url("https://nasdaq.wd1.myworkdayjobs.com/apply", profile)
        assert filler is not None
        assert filler.platform_name() == "workday"

    def test_returns_correct_filler_for_oracle_url(self):
        profile = _make_profile()
        filler = get_filler_for_url("https://oracle.taleo.net/careersection/apply", profile)
        assert filler is not None
        assert filler.platform_name() == "oracle_hcm"

    def test_returns_none_for_unknown_url(self):
        profile = _make_profile()
        filler = get_filler_for_url("https://greenhouse.io/jobs/apply", profile)
        assert filler is None

    def test_filler_has_profile(self):
        profile = _make_profile()
        filler = get_filler_for_url("https://nasdaq.wd1.myworkdayjobs.com/apply", profile)
        assert filler.profile.email == "john@example.com"
