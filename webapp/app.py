import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request


def create_app() -> Flask:
    app = Flask(__name__)
    db_path = os.getenv("MAPS_SCRAPER_DB", "./data/travel_times.sqlite")
    origin_city = os.getenv("MAPS_SCRAPER_ORIGIN", "Golden, CO")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def normalize_direction(value: str) -> str:
        if value == "eastbound":
            return "eastbound"
        return "westbound"

    def resolve_trip(direction: str, destination: str) -> tuple[str, str]:
        if direction == "eastbound":
            return destination, origin_city
        return origin_city, destination

    @app.route("/")
    def index():
        conn = connect()
        try:
            destinations = [
                row[0]
                for row in conn.execute(
                    """
                    SELECT DISTINCT destination
                    FROM travel_times
                    WHERE origin = ?
                    ORDER BY destination
                    """,
                    (origin_city,),
                ).fetchall()
            ]
        finally:
            conn.close()

        return render_template("index.html", destinations=destinations, origin=origin_city)

    @app.route("/api/calendar")
    def calendar():
        destination = request.args.get("destination", "")
        year = request.args.get("year", "")
        direction = normalize_direction(request.args.get("direction", "westbound"))
        if not destination or not year:
            return jsonify({"error": "destination and year are required"}), 400
        origin_value, destination_value = resolve_trip(direction, destination)

        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT date(datetime(observed_at, '-7 hours')) AS day,
                       MAX(duration_seconds) AS max_duration
                FROM travel_times
                WHERE origin = ?
                  AND destination = ?
                  AND strftime('%Y', datetime(observed_at, '-7 hours')) = ?
                GROUP BY day
                ORDER BY day
                """,
                (origin_value, destination_value, year),
            ).fetchall()
        finally:
            conn.close()

        data = {row["day"]: row["max_duration"] for row in rows}
        return jsonify(
            {"destination": destination, "year": year, "direction": direction, "data": data}
        )

    @app.route("/api/day")
    def day():
        destination = request.args.get("destination", "")
        date = request.args.get("date", "")
        direction = normalize_direction(request.args.get("direction", "westbound"))
        if not destination or not date:
            return jsonify({"error": "destination and date are required"}), 400
        origin_value, destination_value = resolve_trip(direction, destination)

        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT strftime('%Y-%m-%dT%H:%M:%S', datetime(observed_at, '-7 hours')) || '-07:00' AS observed_at,
                       duration_seconds
                FROM travel_times
                WHERE origin = ?
                  AND destination = ?
                  AND date(datetime(observed_at, '-7 hours')) = ?
                ORDER BY observed_at
                """,
                (origin_value, destination_value, date),
            ).fetchall()
        finally:
            conn.close()

        data = [
            {
                "observed_at": row["observed_at"],
                "duration_seconds": row["duration_seconds"],
            }
            for row in rows
        ]
        return jsonify(
            {"destination": destination, "date": date, "direction": direction, "data": data}
        )

    @app.route("/api/years")
    def years():
        direction = normalize_direction(request.args.get("direction", "westbound"))
        if direction == "eastbound":
            where_clause = "destination = ?"
        else:
            where_clause = "origin = ?"
        conn = connect()
        try:
            rows = conn.execute(
                f"""
                SELECT DISTINCT strftime('%Y', datetime(observed_at, '-7 hours')) AS year
                FROM travel_times
                WHERE {where_clause}
                ORDER BY year
                """,
                (origin_city,),
            ).fetchall()
        finally:
            conn.close()

        years = [int(row["year"]) for row in rows if row["year"]]
        return jsonify({"years": years})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
