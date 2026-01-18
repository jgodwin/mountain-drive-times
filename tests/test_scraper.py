from datetime import datetime, timezone

import maps_scraper.scraper as scraper


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


def test_fetch_travel_times_parses_response(monkeypatch):
    payload = {
        "status": "OK",
        "rows": [
            {
                "elements": [
                    {
                        "status": "OK",
                        "duration_in_traffic": {"value": 3800},
                        "duration": {"value": 3600},
                        "distance": {"value": 10000},
                    },
                    {
                        "status": "OK",
                        "duration_in_traffic": {"value": 5600},
                        "duration": {"value": 5400},
                        "distance": {"value": 12000},
                    },
                ]
            }
        ],
    }

    def fake_get(*args, **kwargs):
        return FakeResponse(payload)

    monkeypatch.setattr(scraper.requests, "get", fake_get)

    results = scraper.fetch_travel_times(
        api_key="key",
        origin="Golden, CO",
        destinations=["Frisco, CO", "Winter Park, CO"],
    )

    assert [r.destination for r in results] == ["Frisco, CO", "Winter Park, CO"]
    assert [r.duration_seconds for r in results] == [3800, 5600]
    assert [r.distance_meters for r in results] == [10000, 12000]


def test_scrape_once_inserts_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "travel.sqlite"
    observed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    def fake_fetch(*args, **kwargs):
        return [
            scraper.TravelTime("Frisco, CO", 3600, 10000),
            scraper.TravelTime("Winter Park, CO", 5400, 12000),
        ]

    monkeypatch.setattr(scraper, "fetch_travel_times", fake_fetch)

    scraper.scrape_once(
        api_key="key",
        db_path=str(db_path),
        origin="Golden, CO",
        destinations=["Frisco, CO", "Winter Park, CO"],
        observed_at=observed_at,
    )

    conn = scraper.db.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT origin, destination, duration_seconds, distance_meters, observed_at FROM travel_times"
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 2
    assert rows[0][0] == "Golden, CO"
    assert rows[0][1] == "Frisco, CO"
    assert rows[0][2] == 3600
    assert rows[0][3] == 10000
    assert rows[0][4] == observed_at.isoformat()
