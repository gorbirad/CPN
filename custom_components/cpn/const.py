"""Constants for the CPN integration."""

DOMAIN = "cpn"
BASE_URL = "https://www.gov.pl"
NEWS_URL = "https://www.gov.pl/web/energia/wiadomosci"
# Co 15 minut, ale w minutach :05/:20/:35/:50, więc 12:05 jest trafiane
REFRESH_MINUTES = (5, 20, 35, 50)

FUELS = {
    "pb95": "Benzyna 95",
    "pb98": "Benzyna 98",
    "on": "Olej napędowy",
}
