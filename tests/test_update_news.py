from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_news
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "cpn"))
from article_history import select_history


FIXTURE = """
<a href="/web/energia/maksymalna-cena-detaliczna-paliw-obowiazujaca-w-dniach-24-26-pazdziernika-2026-r">
 Maksymalna cena detaliczna paliw obowiązująca w dniach 24-26 października 2026 r.
</a>
<div class="intro">Benzyna 95 - 6,51 zł/l, benzyna 98 - 7,21 zł/l, olej napędowy - 7,99 zł/l.</div>
"""


def scheduled_now() -> datetime:
    return datetime(2026, 10, 23, 10, 40, tzinfo=timezone.utc)


class UpdateNewsTests(unittest.TestCase):
    def test_history_selects_articles_within_last_seven_days(self):
        today = date(2026, 10, 23)
        articles = [
            {"date": date(2026, 10, 12)},
            {"date": date(2026, 10, 23)},
            {"date": date(2026, 10, 17)},
            {"date": date(2026, 10, 16)},
            {"date": date(2026, 10, 20)},
        ]
        selected = select_history(articles, today)
        self.assertEqual(
            [article["date"] for article in selected],
            [
                date(2026, 10, 16),
                date(2026, 10, 17),
                date(2026, 10, 20),
                date(2026, 10, 23),
            ],
        )

    def test_history_falls_back_to_four_latest_old_articles(self):
        today = date(2026, 10, 23)
        articles = [
            {"date": date(2026, 10, 1)},
            {"date": date(2026, 10, 5)},
            {"date": date(2026, 10, 3)},
            {"date": date(2026, 10, 2)},
            {"date": date(2026, 10, 4)},
        ]
        selected = select_history(articles, today)
        self.assertEqual(
            [article["date"] for article in selected],
            [
                date(2026, 10, 2),
                date(2026, 10, 3),
                date(2026, 10, 4),
                date(2026, 10, 5),
            ],
        )

    def test_parses_weekend_article_and_prices(self):
        articles = update_news.parse_articles(FIXTURE)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["date"], "2026-10-24")
        self.assertEqual(articles[0]["prices"], {"pb95": 6.51, "pb98": 7.21, "on": 7.99})

    def test_article_date_handles_range_urls_with_double_hyphen(self):
        base = "/web/energia/maksymalna-cena-detaliczna-paliw-obowiazujaca-"
        cases = {
            "w-dniach-31-pazdziernika--2-listopada-2026-r": date(2026, 10, 31),
            "w-dniach-24-25-pazdziernika-2026-r": date(2026, 10, 24),
            "30-pazdziernika-2026-r": date(2026, 10, 30),
        }
        for suffix, expected in cases.items():
            self.assertEqual(update_news.article_date(base + suffix), expected, suffix)

    def test_business_signature_ignores_order_and_timestamp(self):
        a = update_news.parse_articles(FIXTURE)[0]
        old = {"lastUpdate": "2026-10-23T10:00:00Z", "articles": [a]}
        reordered = {"lastUpdate": "2026-10-23T10:10:00Z", "articles": [dict(a)]}
        self.assertEqual(
            update_news.business_signature(old),
            update_news.business_signature(reordered),
        )

    def test_delayed_workflow_run_still_fetches_outside_publication_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            called = False

            def fetch():
                nonlocal called
                called = True
                return FIXTURE

            self.assertTrue(
                update_news.update_repository(
                    Path(tmp), datetime(2026, 10, 23, 16, 22, tzinfo=timezone.utc), fetch
                )
            )
            self.assertTrue(called)

    def test_lock_blocks_fetch_until_next_noon_warsaw(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("state.json").write_text(
                json.dumps({"disabledUntil": "2026-10-24T10:00:00Z"}), encoding="utf-8"
            )
            called = False

            def fetch():
                nonlocal called
                called = True
                return FIXTURE

            self.assertFalse(update_news.update_repository(root, scheduled_now(), fetch))
            self.assertFalse(called)

    def test_corrupt_state_fails_closed_before_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("state.json").write_text("{broken", encoding="utf-8")
            with self.assertRaises(update_news.ScraperError):
                update_news.update_repository(root, scheduled_now(), lambda: self.fail("fetched"))

    def test_state_with_wrong_json_shape_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("state.json").write_text("[]", encoding="utf-8")
            with self.assertRaises(update_news.ScraperError):
                update_news.update_repository(root, scheduled_now(), lambda: self.fail("fetched"))

    def test_changed_data_updates_news_and_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(update_news.update_repository(root, scheduled_now(), lambda: FIXTURE))
            news = json.loads(root.joinpath("news.json").read_text(encoding="utf-8"))
            state = json.loads(root.joinpath("state.json").read_text(encoding="utf-8"))
            self.assertEqual(news["articles"][0]["date"], "2026-10-24")
            self.assertEqual(state["disabledUntil"], "2026-10-24T10:00:00Z")

    def test_unchanged_business_data_does_not_rewrite_or_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("news.json").write_text(
                json.dumps(
                    {
                        "lastUpdate": "2026-10-23T10:00:00Z",
                        "articles": update_news.parse_articles(FIXTURE),
                    }
                ),
                encoding="utf-8",
            )
            self.assertFalse(update_news.update_repository(root, scheduled_now(), lambda: FIXTURE))
            self.assertFalse(root.joinpath("state.json").exists())

    def test_changed_price_updates_json_and_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = update_news.parse_articles(FIXTURE)[0]
            root.joinpath("news.json").write_text(
                json.dumps(
                    {
                        "lastUpdate": "2026-10-23T10:00:00Z",
                        "articles": [article],
                    }
                ),
                encoding="utf-8",
            )
            changed = FIXTURE.replace("6,51", "6,52")
            self.assertTrue(
                update_news.update_repository(root, scheduled_now(), lambda: changed)
            )
            data = json.loads(root.joinpath("news.json").read_text(encoding="utf-8"))
            self.assertEqual(data["articles"][0]["prices"]["pb95"], 6.52)


if __name__ == "__main__":
    unittest.main()
