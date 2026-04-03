"""Oracle HCM form filler — handles JPMorgan, Oracle, and other Taleo/OracleCloud ATS."""
from src.applier.base import BaseFormFiller, FillResult
from src.applier.registry import register_filler
from src.models.user_profile import UserProfile

# Selectors for Oracle HCM / Taleo forms
_FIELD_SELECTORS = [
    ("first_name", "input[aria-label*='First']"),
    ("first_name", "input[aria-label*='first']"),
    ("last_name", "input[aria-label*='Last']"),
    ("last_name", "input[aria-label*='last']"),
    ("email", "input[aria-label*='Email']"),
    ("email", "input[aria-label*='email']"),
    ("phone", "input[aria-label*='Phone']"),
    ("phone", "input[aria-label*='phone']"),
]

_SUBMIT_SELECTORS = [
    "button:has-text('Submit')",
    "button:has-text('Submit Application')",
    "input[type='submit']",
]


class OracleHCMFiller(BaseFormFiller):
    def platform_name(self) -> str:
        return "oracle_hcm"

    def can_handle(self, url: str) -> bool:
        return (
            "taleo.net" in url
            or "oraclecloud.com" in url
            or "fa.us" in url and "oraclecloud" in url
        )

    def fill_form(self, page) -> FillResult:
        profile = self.profile
        field_values = {
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": profile.email,
            "phone": profile.phone,
        }

        filled: list[str] = []
        skipped: list[str] = []
        seen_fields: set[str] = set()

        for field_name, selector in _FIELD_SELECTORS:
            if field_name in seen_fields:
                continue
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.fill(field_values[field_name])
                filled.append(field_name)
                seen_fields.add(field_name)

        # Track which fields were never found
        for field_name in field_values:
            if field_name not in seen_fields:
                skipped.append(field_name)

        # Resume upload
        file_el = page.query_selector("input[type='file']")
        if file_el and file_el.is_visible():
            page.set_input_files("input[type='file']", profile.resume_path)
            filled.append("resume")
        else:
            skipped.append("resume")

        return FillResult(
            success=len(filled) > 0,
            fields_filled=filled,
            fields_skipped=skipped,
        )

    def submit(self, page) -> bool:
        for selector in _SUBMIT_SELECTORS:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                return True
        return False


register_filler(OracleHCMFiller)
