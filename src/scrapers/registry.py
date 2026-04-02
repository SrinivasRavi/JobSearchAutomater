"""Scraper registry — maps source names to adapter instances."""
import logging
import yaml
import os
from typing import Optional

from src.scrapers.base import BaseScraper

logger = logging.getLogger("jobsearch.registry")

# Map of source name -> adapter class
_ADAPTER_MAP: dict[str, type[BaseScraper]] = {}

DEFAULT_PROFILE = "mumbai"


def register_adapter(source_name: str, adapter_class: type[BaseScraper]):
    _ADAPTER_MAP[source_name] = adapter_class


def _load_config() -> dict:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config", "sources.yaml"
    )
    with open(config_path) as f:
        return yaml.safe_load(f)


def list_profiles() -> list[str]:
    """Return available profile names."""
    config = _load_config()
    return list(config.get("profiles", {}).keys())


def get_scrapers(
    profile: Optional[str] = None,
    source_filter: Optional[str] = None,
) -> list[BaseScraper]:
    """Build scraper instances from config. Only returns sources with registered adapters."""
    _import_adapters()
    config = _load_config()

    profile_name = profile or DEFAULT_PROFILE
    profiles = config.get("profiles", {})

    if profile_name not in profiles:
        logger.error("Profile '%s' not found. Available: %s",
                     profile_name, list(profiles.keys()))
        return []

    sources = profiles[profile_name].get("sources", [])
    scrapers = []

    for source in sources:
        name = source["name"]
        if source.get("enabled") is False:
            continue
        if source_filter and name != source_filter:
            continue
        if name in _ADAPTER_MAP:
            scrapers.append(_ADAPTER_MAP[name](source["url"]))
        else:
            logger.debug("No adapter registered for source '%s', skipping", name)

    return scrapers


def _import_adapters():
    """Import all adapter modules so they register themselves."""
    for module in [
        "src.scrapers.amazon",
        "src.scrapers.barclays",
        "src.scrapers.citi",
        "src.scrapers.nomura",
        "src.scrapers.deutsche_bank",
        "src.scrapers.visa",
        "src.scrapers.msci",
        "src.scrapers.morningstar",
        "src.scrapers.goldman_sachs",
        "src.scrapers.jpmorgan",
        "src.scrapers.oracle_careers",
        "src.scrapers.microsoft",
        "src.scrapers.nasdaq",
        "src.scrapers.bofa",
        "src.scrapers.google",
    ]:
        try:
            __import__(module)
        except ImportError:
            pass
