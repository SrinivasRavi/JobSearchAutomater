"""ATS URL resolver — navigates to a job detail page and clicks the Apply button."""

_APPLY_SELECTORS = [
    "button:has-text('Apply')",
    "a:has-text('Apply')",
    "button:has-text('Apply Now')",
    "a:has-text('Apply Now')",
    "button:has-text('Apply for Job')",
    "[data-automation-id='apply']",
    "[data-automation-id='applyButton']",
    "a[href*='apply']",
]


class ApplyUrlResolver:
    def resolve_apply_page(self, page, job_link: str) -> bool:
        """Navigate to job_link and click the Apply button.

        Returns True if an Apply button was found and clicked, False otherwise.
        """
        page.goto(job_link, wait_until="domcontentloaded")
        for selector in _APPLY_SELECTORS:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_load_state("domcontentloaded")
                return True
        return False
