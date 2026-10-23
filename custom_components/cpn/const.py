"""Constants for the CPN integration."""

DOMAIN = "cpn"
NEWS_JSON_URL = "https://gorbirad.github.io/CPN/news.json"
# Odświeżanie cache'u HA co 15 minut, w minutach :05/:20/:35/:50.
REFRESH_MINUTES = (5, 20, 35, 50)
CACHE_TTL_SECONDS = 60 * 60
FEED_REFRESH_VERSION = "1.1.2"

FUELS = {
    "pb95": "Benzyna 95",
    "pb98": "Benzyna 98",
    "on": "Olej napędowy",
}
