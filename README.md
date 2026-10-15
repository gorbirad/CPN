# CPN – maksymalne ceny detaliczne paliw

Integracja Home Assistant. Co 15 minut sprawdza stronę
[gov.pl/web/energia/wiadomosci](https://www.gov.pl/web/energia/wiadomosci), znajduje najnowszy
artykuł „Maksymalna cena detaliczna paliw…” i tworzy sensory (PLN/l):

- `sensor.cpn_pb95` – Benzyna 95
- `sensor.cpn_pb98` – Benzyna 98
- `sensor.cpn_on` – Olej napędowy

Atrybuty: `title`, `url`, `summary`.

## Instalacja

**Ręcznie:** skopiuj `custom_components/cpn` do katalogu `config/custom_components/`, zrestartuj HA.
**HACS:** Custom repositories → `https://github.com/gorbirad/CPN` (Integration).

Następnie: Ustawienia → Urządzenia i usługi → Dodaj integrację → **CPN**.
