import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import requests

from maps_scraper import db


@dataclass(frozen=True)
class TravelTime:
    destination: str
    duration_seconds: int
    distance_meters: int | None


def fetch_travel_times(
    api_key: str,
    origin: str,
    destinations: Iterable[str],
    timeout_seconds: int = 15,
) -> list[TravelTime]:
    destination_list = list(destinations)
    if not destination_list:
        return []

    response = requests.get(
        "https://maps.googleapis.com/maps/api/distancematrix/json",
        params={
            "origins": origin,
            "destinations": "|".join(destination_list),
            "mode": "driving",
            "departure_time": "now",
            "key": api_key,
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "OK":
        raise RuntimeError(f"API error: {payload.get('status')}")

    rows = payload.get("rows", [])
    if not rows:
        raise RuntimeError("API response missing rows")

    elements = rows[0].get("elements", [])
    if len(elements) != len(destination_list):
        raise RuntimeError("API response destination count mismatch")

    results: list[TravelTime] = []
    for destination, element in zip(destination_list, elements):
        if element.get("status") != "OK":
            raise RuntimeError(
                f"API element error for {destination}: {element.get('status')}"
            )
        duration = element.get("duration_in_traffic", {}).get("value")
        if duration is None:
            duration = element.get("duration", {}).get("value")
        distance = element.get("distance", {}).get("value")
        if duration is None:
            raise RuntimeError(f"Missing duration for {destination}")
        results.append(
            TravelTime(
                destination=destination,
                duration_seconds=int(duration),
                distance_meters=int(distance) if distance is not None else None,
            )
        )

    return results


def scrape_once(
    api_key: str,
    db_path: str,
    origin: str,
    destinations: Iterable[str],
    observed_at: datetime | None = None,
) -> list[TravelTime]:
    destination_list = list(destinations)
    travel_times = fetch_travel_times(api_key, origin, destination_list)
    timestamp = (observed_at or datetime.now(timezone.utc)).isoformat()
    reverse_times: list[TravelTime] = []
    reverse_rows: list[tuple[str, str, int, int | None, str]] = []
    for destination in destination_list:
        reverse_entries = fetch_travel_times(api_key, destination, [origin])
        if not reverse_entries:
            continue
        reverse_entry = reverse_entries[0]
        reverse_times.append(reverse_entry)
        reverse_rows.append(
            (
                destination,
                reverse_entry.destination,
                reverse_entry.duration_seconds,
                reverse_entry.distance_meters,
                timestamp,
            )
        )

    conn = db.connect(db_path)
    try:
        db.init_db(conn)
        db.insert_travel_times(
            conn,
            [
                (origin, entry.destination, entry.duration_seconds, entry.distance_meters, timestamp)
                for entry in travel_times
            ],
        )
        if reverse_rows:
            db.insert_travel_times(conn, reverse_rows)
    finally:
        conn.close()

    return travel_times + reverse_times


def run_forever(
    api_key: str,
    db_path: str,
    origin: str,
    destinations: Iterable[str],
    interval_seconds: int,
) -> None:
    while True:
        scrape_once(api_key, db_path, origin, destinations)
        time.sleep(interval_seconds)
