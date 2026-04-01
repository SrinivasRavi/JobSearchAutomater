"""Tests for URL cleaning utility."""
import pytest

from src.utils.url_cleaner import clean_job_link


class TestCleanJobLink:
    def test_strips_query_params(self):
        url = "https://careers.example.com/jobs/123?ref=search&utm_source=google"
        assert clean_job_link(url) == "https://careers.example.com/jobs/123"

    def test_strips_fragment(self):
        url = "https://careers.example.com/jobs/123#apply"
        assert clean_job_link(url) == "https://careers.example.com/jobs/123"

    def test_strips_both_query_and_fragment(self):
        url = "https://careers.example.com/jobs/123?ref=x#top"
        assert clean_job_link(url) == "https://careers.example.com/jobs/123"

    def test_preserves_path(self):
        url = "https://careers.example.com/en-us/jobs/software-engineer/456"
        assert clean_job_link(url) == "https://careers.example.com/en-us/jobs/software-engineer/456"

    def test_strips_trailing_slash(self):
        url = "https://careers.example.com/jobs/123/"
        assert clean_job_link(url) == "https://careers.example.com/jobs/123"

    def test_lowercases_scheme_and_host(self):
        url = "HTTPS://Careers.Example.COM/Jobs/123"
        assert clean_job_link(url) == "https://careers.example.com/Jobs/123"

    def test_preserves_required_query_params(self):
        """Some sources encode job ID in query params. Override list should preserve them."""
        url = "https://jobs.example.com/search?jobId=ABC123&ref=google"
        result = clean_job_link(url, keep_params=["jobId"])
        assert result == "https://jobs.example.com/search?jobId=ABC123"

    def test_preserves_multiple_required_params(self):
        url = "https://jobs.example.com/search?jobId=ABC&siteId=5&ref=x"
        result = clean_job_link(url, keep_params=["jobId", "siteId"])
        assert result == "https://jobs.example.com/search?jobId=ABC&siteId=5"

    def test_empty_string_returns_empty(self):
        assert clean_job_link("") == ""

    def test_url_with_no_path(self):
        url = "https://careers.example.com"
        assert clean_job_link(url) == "https://careers.example.com"

    def test_idempotent(self):
        url = "https://careers.example.com/jobs/123?ref=x"
        cleaned = clean_job_link(url)
        assert clean_job_link(cleaned) == cleaned
