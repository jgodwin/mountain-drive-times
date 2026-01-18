import sys

from maps_scraper.config import load_config
from maps_scraper.scraper import run_forever, scrape_once


def main() -> int:
    config = load_config()

    if "--once" in sys.argv:
        scrape_once(
            api_key=config.api_key,
            db_path=config.db_path,
            origin=config.origin,
            destinations=config.destinations,
        )
        return 0

    run_forever(
        api_key=config.api_key,
        db_path=config.db_path,
        origin=config.origin,
        destinations=config.destinations,
        interval_seconds=config.interval_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
