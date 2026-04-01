"""Job data model."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from src.models.enums import ApplicationStatus, SourceType


@dataclass
class Job:
    company_name: str
    job_title: str
    job_description: str
    job_link: str
    clean_job_link: str
    scraped_timestamp: datetime
    application_status: ApplicationStatus
    source_type: SourceType
    source_name: str
    posted_timestamp: Optional[datetime] = None
    job_id: Optional[int] = None

    @property
    def dedupe_key(self) -> str:
        return self.clean_job_link

    def to_dict(self) -> dict:
        d = asdict(self)
        d["application_status"] = self.application_status.value
        d["source_type"] = self.source_type.value
        if self.scraped_timestamp:
            d["scraped_timestamp"] = self.scraped_timestamp.isoformat()
        if self.posted_timestamp:
            d["posted_timestamp"] = self.posted_timestamp.isoformat()
        return d
