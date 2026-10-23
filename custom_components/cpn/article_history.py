"""Select fuel-price articles to import as initial history."""
from __future__ import annotations

from datetime import date

HISTORY_DAYS = 7
HISTORY_FALLBACK_ITEMS = 4


def select_history(articles: list[dict], today: date) -> list[dict]:
    """Return the last week's articles, or the four latest when the week is empty."""
    dated = sorted(
        (article for article in articles if article.get("date") and article["date"] <= today),
        key=lambda article: article["date"],
        reverse=True,
    )
    recent = [
        article
        for article in dated
        if (today - article["date"]).days <= HISTORY_DAYS
    ]
    selected = recent or dated[:HISTORY_FALLBACK_ITEMS]
    return sorted(selected, key=lambda article: article["date"])
