import argparse
import os
import random
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from maps_scraper import db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed fake travel-time data into the SQLite database.",
    )
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing rows for the year before inserting.",
    )
    return parser.parse_args()


def build_fake_duration(randomizer: random.Random, destination: str, when: datetime) -> int:
    base = 3600 if "Frisco" in destination else 4200
    weekend = 1.2 if when.weekday() >= 5 else 1.0
    hour = when.hour
    rush = 1.0
    if 6 <= hour <= 9:
        rush = 1.25
    elif 15 <= hour <= 18:
        rush = 1.35
    noise = randomizer.randint(-300, 420)
    return max(1200, int(base * weekend * rush + noise))


def main() -> int:
    args = parse_args()
    load_dotenv()

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

    randomizer = random.Random(args.seed)
    start = datetime(args.year, 1, 1, tzinfo=timezone.utc)
    end = datetime(args.year + 1, 1, 1, tzinfo=timezone.utc)

    conn = db.connect(db_path)
    try:
        db.init_db(conn)
        if args.clear:
            conn.execute(
                "DELETE FROM travel_times WHERE substr(observed_at, 1, 4) = ?",
                (str(args.year),),
            )
            conn.commit()

        rows = []
        current = start
        while current < end:
            for destination in destinations:
                duration = build_fake_duration(randomizer, destination, current)
                rows.append(
                    (
                        origin,
                        destination,
                        duration,
                        None,
                        current.isoformat(),
                    )
                )
                reverse_duration = build_fake_duration(randomizer, origin, current)
                rows.append(
                    (
                        destination,
                        origin,
                        reverse_duration,
                        None,
                        current.isoformat(),
                    )
                )
            current += timedelta(hours=1)

        db.insert_travel_times(conn, rows)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
