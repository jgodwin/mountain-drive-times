import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request


def create_app() -> Flask:
    app = Flask(__name__)
    db_path = os.getenv("MAPS_SCRAPER_DB", "./data/travel_times.sqlite")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @app.route("/")
    def index():
        conn = connect()
        try:
            destinations = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT destination FROM travel_times ORDER BY destination"
                ).fetchall()
            ]
        finally:
            conn.close()

        return render_template("index.html", destinations=destinations)

    @app.route("/api/calendar")
    def calendar():
        destination = request.args.get("destination", "")
        year = request.args.get("year", "")
        if not destination or not year:
            return jsonify({"error": "destination and year are required"}), 400

        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT substr(observed_at, 1, 10) AS day,
                       MAX(duration_seconds) AS max_duration
                FROM travel_times
                WHERE destination = ?
                  AND substr(observed_at, 1, 4) = ?
                GROUP BY day
                ORDER BY day
                """,
                (destination, year),
            ).fetchall()
        finally:
            conn.close()

        data = {row["day"]: row["max_duration"] for row in rows}
        return jsonify({"destination": destination, "year": year, "data": data})

    @app.route("/api/day")
    def day():
        destination = request.args.get("destination", "")
        date = request.args.get("date", "")
        if not destination or not date:
            return jsonify({"error": "destination and date are required"}), 400

        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT observed_at, duration_seconds
                FROM travel_times
                WHERE destination = ?
                  AND substr(observed_at, 1, 10) = ?
                ORDER BY observed_at
                """,
                (destination, date),
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
        return jsonify({"destination": destination, "date": date, "data": data})

    @app.route("/api/years")
    def years():
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT DISTINCT substr(observed_at, 1, 4) AS year FROM travel_times ORDER BY year"
            ).fetchall()
        finally:
            conn.close()

        years = [int(row["year"]) for row in rows if row["year"]]
        return jsonify({"years": years})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
