"""Constants for the CPN integration."""
from datetime import timedelta

DOMAIN = "cpn"
BASE_URL = "https://www.gov.pl"
NEWS_URL = "https://www.gov.pl/web/energia/wiadomosci"
SCAN_INTERVAL = timedelta(minutes=15)

FUELS = {
    "pb95": "Benzyna 95",
    "pb98": "Benzyna 98",
    "on": "Olej napędowy",
}
