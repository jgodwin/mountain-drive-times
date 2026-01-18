from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def slugify(label: str, used: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.strip().lower())
    slug = slug.strip("-")
    if not slug:
        slug = "destination"
    base = slug
    counter = 2
    while slug in used:
        slug = f"{base}-{counter}"
        counter += 1
    used.add(slug)
    return slug


def export_index(conn: sqlite3.Connection) -> tuple[list[dict], list[int]]:
    destinations = [
        row["destination"]
        for row in conn.execute(
            "SELECT DISTINCT destination FROM travel_times ORDER BY destination"
        ).fetchall()
    ]
    years = [
        int(row["year"])
        for row in conn.execute(
            "SELECT DISTINCT strftime('%Y', datetime(observed_at, '-7 hours')) AS year FROM travel_times ORDER BY year"
        ).fetchall()
        if row["year"]
    ]

    used_slugs: set[str] = set()
    dest_entries = [
        {"id": slugify(destination, used_slugs), "label": destination}
        for destination in destinations
    ]
    return dest_entries, years


def export_calendar(
    conn: sqlite3.Connection,
    destination: str,
    year: int,
) -> dict:
    rows = conn.execute(
        """
        SELECT date(datetime(observed_at, '-7 hours')) AS day,
               MAX(duration_seconds) AS max_duration
        FROM travel_times
        WHERE destination = ?
          AND strftime('%Y', datetime(observed_at, '-7 hours')) = ?
        GROUP BY day
        ORDER BY day
        """,
        (destination, str(year)),
    ).fetchall()
    return {row["day"]: row["max_duration"] for row in rows}


def export_day_details(
    conn: sqlite3.Connection, destination: str
) -> dict[str, list[dict]]:
    rows = conn.execute(
        """
        SELECT date(datetime(observed_at, '-7 hours')) AS day,
               strftime('%Y-%m-%dT%H:%M:%S', datetime(observed_at, '-7 hours')) || '-07:00' AS observed_at,
               duration_seconds
        FROM travel_times
        WHERE destination = ?
        ORDER BY observed_at
        """,
        (destination,),
    ).fetchall()
    data: dict[str, list[dict]] = {}
    for row in rows:
        day = row["day"]
        data.setdefault(day, []).append(
            {
                "observed_at": row["observed_at"],
                "duration_seconds": row["duration_seconds"],
            }
        )
    return data


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


def build_static_site(db_path: str, out_dir: Path, clean: bool) -> None:
    if clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    static_src = Path("webapp/static")
    static_dest = out_dir / "static"
    shutil.copytree(static_src, static_dest, dirs_exist_ok=True)

    index_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mountain Drive Times</title>
  <link rel="stylesheet" href="static/css/style.css" />
</head>
<body data-source="static" data-base="data">
  <main class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">Golden, CO travel times</p>
        <h1>Mountain Drive Times</h1>
        <p class="subhead">
          Hourly snapshots of drive time from Golden to your favorite ski towns.
        </p>
      </div>
      <div class="controls">
        <label>
          Destination
          <select id="destination-select"></select>
        </label>
        <label>
          Year
          <select id="year-select"></select>
        </label>
      </div>
    </header>

    <section class="calendar-section">
      <div class="calendar-wrap">
        <div id="calendar" class="calendar"></div>
        <aside class="legend">
          <div class="legend-title">Max daily drive time</div>
          <div class="legend-bar" id="legend-bar"></div>
          <div class="legend-labels">
            <span id="legend-min">1h</span>
            <span id="legend-max">3h</span>
          </div>
        </aside>
      </div>
    </section>

    <div class="modal" id="detail-modal" aria-hidden="true">
      <div class="modal-backdrop" data-modal-close></div>
      <div class="modal-panel" role="dialog" aria-modal="true">
        <button class="modal-close" type="button" data-modal-close aria-label="Close">×</button>
        <div class="detail-header">
          <div>
            <h2 id="detail-title">Select a day</h2>
            <p id="detail-subtitle">Click a calendar tile to see hourly drive times.</p>
          </div>
          <div class="detail-meta" id="detail-meta"></div>
        </div>
        <div class="chart" id="detail-chart"></div>
      </div>
    </div>
  </main>

  <script src="static/js/app.js"></script>
</body>
</html>
"""
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    data_root = out_dir / "data"
    if clean and data_root.exists():
        shutil.rmtree(data_root)
    data_root.mkdir(parents=True, exist_ok=True)

    with connect(db_path) as conn:
        destinations, years = export_index(conn)
        write_json(data_root / "index.json", {"destinations": destinations, "years": years})

        for dest in destinations:
            dest_id = dest["id"]
            label = dest["label"]
            for year in years:
                calendar_data = export_calendar(conn, label, year)
                write_json(
                    data_root / "calendar" / dest_id / f"{year}.json",
                    {"destination": label, "year": year, "data": calendar_data},
                )

            day_details = export_day_details(conn, label)
            for day, entries in day_details.items():
                write_json(
                    data_root / "day" / dest_id / f"{day}.json",
                    {"destination": label, "date": day, "data": entries},
                )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a static bundle for the travel times dashboard."
    )
    parser.add_argument(
        "--db",
        default=os.getenv("MAPS_SCRAPER_DB", "./data/travel_times.sqlite"),
        help="Path to the sqlite database.",
    )
    parser.add_argument(
        "--out",
        default="webapp/static_site",
        help="Output directory for the static site bundle.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the output directory before rebuilding.",
    )
    args = parser.parse_args()

    build_static_site(args.db, Path(args.out), args.clean)


if __name__ == "__main__":
    main()
