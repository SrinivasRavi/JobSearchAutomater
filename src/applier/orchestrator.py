"""Apply orchestrator — drives Playwright to fill and submit job applications."""
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import sync_playwright

from src.applier.base import BaseFormFiller
from src.applier.registry import get_filler_for_url
# Import fillers so they self-register into the registry
import src.applier.oracle_hcm  # noqa: F401
import src.applier.workday  # noqa: F401
from src.models.user_profile import UserProfile
from src.persistence.repository import ApplicationRepository

logger = logging.getLogger(__name__)


@dataclass
class ApplyResult:
    status: str  # SUBMITTED, FAILED, SKIPPED
    fields_filled: list[str]
    fields_skipped: list[str]
    failure_reason: str = ""
    app_id: Optional[int] = None


SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "screenshots",
)


def check_ats_support(url: str, profile: UserProfile) -> Optional[BaseFormFiller]:
    """Check if we have a filler for this URL. Returns the filler or None."""
    return get_filler_for_url(url, profile)


class ApplyOrchestrator:
    def __init__(self, conn: sqlite3.Connection, profile: UserProfile):
        self._conn = conn
        self._profile = profile
        self._app_repo = ApplicationRepository(conn)

    def mark_unsupported(
        self,
        job_url: str,
        job_id: Optional[int] = None,
        job_title: str = "",
        company_name: str = "",
    ) -> int:
        """Record a job as UNSUPPORTED_ATS without opening a browser."""
        app_id = self._app_repo.create_application(
            job_id=job_id,
            profile_name=self._profile.profile_id,
            job_url=job_url,
            job_title=job_title,
            company_name=company_name,
            ats_platform="unknown",
        )
        self._app_repo.update_status(app_id, "FAILED", failure_reason="UNSUPPORTED_ATS")
        self._app_repo.log_attempt(app_id, result="FAILED", error_message="UNSUPPORTED_ATS")
        return app_id

    def apply_with_filler(
        self,
        filler: BaseFormFiller,
        job_url: str,
        job_id: Optional[int] = None,
        job_title: str = "",
        company_name: str = "",
    ) -> ApplyResult:
        """Open browser, fill form, prompt for submission. Returns ApplyResult.

        The caller must provide a valid filler (use check_ats_support first).
        """
        app_id = self._app_repo.create_application(
            job_id=job_id,
            profile_name=self._profile.profile_id,
            job_url=job_url,
            job_title=job_title,
            company_name=company_name,
            ats_platform=filler.platform_name(),
        )

        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        before_shot = os.path.join(SCREENSHOTS_DIR, f"{app_id}_before.png")
        after_shot = os.path.join(SCREENSHOTS_DIR, f"{app_id}_after.png")

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=False)
                with browser.new_context() as ctx:
                    page = ctx.new_page()
                    page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(5000)
                    page.screenshot(path=before_shot)

                    fill_result = filler.fill_form(page)
                    page.screenshot(path=after_shot)

                    self._print_summary(job_title, company_name, fill_result)
                    answer = input("Submit? [y/n/skip]: ").strip().lower()

                    if answer == "y":
                        filler.submit(page)
                        self._app_repo.update_status(app_id, "SUBMITTED")
                        self._app_repo.log_attempt(
                            app_id, result="SUCCESS", screenshot_path=after_shot
                        )
                        return ApplyResult(
                            status="SUBMITTED",
                            fields_filled=fill_result.fields_filled,
                            fields_skipped=fill_result.fields_skipped,
                            app_id=app_id,
                        )
                    elif answer == "n":
                        self._app_repo.update_status(
                            app_id, "FAILED", failure_reason="HUMAN_REJECTED"
                        )
                        self._app_repo.log_attempt(
                            app_id, result="FAILED",
                            error_message="HUMAN_REJECTED",
                            screenshot_path=after_shot,
                        )
                        return ApplyResult(
                            status="FAILED",
                            fields_filled=fill_result.fields_filled,
                            fields_skipped=fill_result.fields_skipped,
                            failure_reason="HUMAN_REJECTED",
                            app_id=app_id,
                        )
                    else:  # skip
                        self._app_repo.update_status(app_id, "SKIPPED")
                        self._app_repo.log_attempt(
                            app_id, result="SKIPPED", screenshot_path=after_shot
                        )
                        return ApplyResult(
                            status="SKIPPED",
                            fields_filled=fill_result.fields_filled,
                            fields_skipped=fill_result.fields_skipped,
                            app_id=app_id,
                        )
        except Exception as e:
            logger.error("Apply failed for %s: %s", job_url, e)
            self._app_repo.update_status(app_id, "FAILED", failure_reason=str(e))
            self._app_repo.log_attempt(app_id, result="FAILED", error_message=str(e))
            return ApplyResult(
                status="FAILED",
                fields_filled=[],
                fields_skipped=[],
                failure_reason=str(e),
                app_id=app_id,
            )

    @staticmethod
    def _print_summary(job_title: str, company_name: str, fill_result) -> None:
        print(f"\n--- Form Filled ---")
        print(f"Job:     {job_title} @ {company_name}")
        print(f"Filled:  {', '.join(fill_result.fields_filled) or 'none'}")
        print(f"Skipped: {', '.join(fill_result.fields_skipped) or 'none'}")
        if fill_result.error:
            print(f"Error:   {fill_result.error}")
        print()
