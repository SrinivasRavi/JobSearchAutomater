"""Scraper registry — maps source names to adapter instances."""
import yaml
import os
from typing import Optional

from src.scrapers.base import BaseScraper

# Map of source name -> adapter class
_ADAPTER_MAP: dict[str, type[BaseScraper]] = {}


def register_adapter(source_name: str, adapter_class: type[BaseScraper]):
    _ADAPTER_MAP[source_name] = adapter_class


def _load_sources_config() -> list[dict]:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config", "sources.yaml"
    )
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config.get("sources", [])


def get_scrapers(source_filter: Optional[str] = None) -> list[BaseScraper]:
    """Build scraper instances from config. Only returns sources with registered adapters."""
    # Import adapters to trigger registration
    _import_adapters()

    sources = _load_sources_config()
    scrapers = []

    for source in sources:
        name = source["name"]
        if source_filter and name != source_filter:
            continue
        if name in _ADAPTER_MAP:
            scrapers.append(_ADAPTER_MAP[name](source["url"]))

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
    ]:
        try:
            __import__(module)
        except ImportError:
            pass
