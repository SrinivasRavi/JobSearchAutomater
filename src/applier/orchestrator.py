"""Apply orchestrator — drives Playwright to fill and submit job applications."""
import os
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import sync_playwright

from src.applier.registry import get_filler_for_url
# Import fillers so they self-register into the registry
import src.applier.oracle_hcm  # noqa: F401
import src.applier.workday  # noqa: F401
from src.models.user_profile import UserProfile
from src.persistence.repository import ApplicationRepository


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


class ApplyOrchestrator:
    def __init__(self, conn: sqlite3.Connection, profile: UserProfile):
        self._conn = conn
        self._profile = profile
        self._app_repo = ApplicationRepository(conn)

    def apply_to_url(
        self,
        job_url: str,
        job_id: Optional[int] = None,
        job_title: str = "",
        company_name: str = "",
    ) -> ApplyResult:
        """Full apply flow for a single job URL. Returns ApplyResult."""
        filler = get_filler_for_url(job_url, self._profile)
        if filler is None:
            app_id = self._app_repo.create_application(
                job_id=job_id,
                profile_name=self._profile.profile_name,
                job_url=job_url,
                job_title=job_title,
                company_name=company_name,
                ats_platform="unknown",
            )
            self._app_repo.update_status(app_id, "FAILED", failure_reason="UNSUPPORTED_ATS")
            self._app_repo.log_attempt(app_id, result="FAILED", error_message="UNSUPPORTED_ATS")
            return ApplyResult(
                status="FAILED",
                fields_filled=[],
                fields_skipped=[],
                failure_reason="UNSUPPORTED_ATS",
                app_id=app_id,
            )

        app_id = self._app_repo.create_application(
            job_id=job_id,
            profile_name=self._profile.profile_name,
            job_url=job_url,
            job_title=job_title,
            company_name=company_name,
            ats_platform=filler.platform_name(),
        )

        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        before_shot = os.path.join(SCREENSHOTS_DIR, f"{app_id}_before.png")
        after_shot = os.path.join(SCREENSHOTS_DIR, f"{app_id}_after.png")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            with browser.new_context() as ctx:
                page = ctx.new_page()
                page.goto(job_url, wait_until="domcontentloaded")
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
                else:  # skip or anything else
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

    @staticmethod
    def _print_summary(job_title: str, company_name: str, fill_result) -> None:
        print(f"\n--- Form Filled ---")
        print(f"Job:     {job_title} @ {company_name}")
        print(f"Filled:  {', '.join(fill_result.fields_filled) or 'none'}")
        print(f"Skipped: {', '.join(fill_result.fields_skipped) or 'none'}")
        if fill_result.error:
            print(f"Error:   {fill_result.error}")
        print()
