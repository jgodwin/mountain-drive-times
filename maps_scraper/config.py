import os

from dotenv import load_dotenv
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    api_key: str
    db_path: str
    origin: str
    destinations: tuple[str, ...]
    interval_seconds: int


def load_config() -> Config:
    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    db_path = os.getenv("MAPS_SCRAPER_DB", "./data/travel_times.sqlite")
    origin = os.getenv("MAPS_SCRAPER_ORIGIN", "Golden, CO")
    destinations = tuple(
        d.strip()
        for d in os.getenv(
            "MAPS_SCRAPER_DESTINATIONS",
            "Frisco, CO;Winter Park, CO",
        ).split(";")
        if d.strip()
    )
    interval_seconds = int(os.getenv("MAPS_SCRAPER_INTERVAL_SECONDS", "3600"))

    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY is required")

    return Config(
        api_key=api_key,
        db_path=db_path,
        origin=origin,
        destinations=destinations,
        interval_seconds=interval_seconds,
    )
