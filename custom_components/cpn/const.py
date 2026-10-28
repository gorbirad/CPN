"""Constants for the CPN integration."""

DOMAIN = "cpn"
NEWS_JSON_URL = "https://gorbirad.github.io/CPN/news.json"
# HA sprawdza feed co 5 minut; faktyczne pobranie zależy od adaptacyjnego TTL cache'u.
REFRESH_MINUTES = tuple(range(0, 60, 5))
# Szybkie sprawdzanie w oknie publikacji (czas Europe/Warsaw), dopóki feed nie zawiera
# artykułu na jutro; potem wolne odświeżanie.
CACHE_TTL_FAST_SECONDS = 4 * 60
CACHE_TTL_SLOW_SECONDS = 60 * 60
FAST_WINDOW_START_HOUR = 11
FAST_WINDOW_END_HOUR = 17
FEED_REFRESH_VERSION = "1.1.2"

FUELS = {
    "pb95": "Benzyna 95",
    "pb98": "Benzyna 98",
    "on": "Olej napędowy",
}
