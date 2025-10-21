# scrapers/__init__.py
from .jobs import scrape_jobs
from .accommodations import scrape_accommodations

__all__ = ["scrape_jobs", "scrape_accommodations"]