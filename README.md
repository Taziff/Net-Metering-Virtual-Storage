# Net Metering Virtual Storage for Home Assistant

Uniwersalna integracja dla Home Assistant umożliwiająca dokładne odwzorowanie i śledzenie stanu **wirtualnego magazynu energii (systemu opustów / net-meteringu)** u dowolnego dystrybutora energii (PGE, Tauron, Enea, Energa itp.). 

Integracja automatycznie uwzględnia współczynnik korekcyjny (np. 0.8 lub 0.7) oraz realizuje zasadę **FIFO (First-In, First-Out)**, zużywając prąd w pierwszej kolejności z najstarszych paczek energii, zachowując ich 12-miesięczny okres ważności.

## Główne cechy

* **Dwuetapowa konfiguracja graficzna (UI):** Formularz pozwala wybrać encje liczników oraz przepisać stany z faktury bez dotykania plików YAML.
* **Rozbicie na miesiące:** Stan magazynu jest podzielony na 12 miesięcy, widocznych jako atrybuty encji.
* **Dwa sensory główne:**
  * `sensor.wirtualny_magazyn_energia_wprowadzona` – stan surowy wirtualnego magazynu przed rozliczeniem.
  * `sensor.wirtualny_magazyn_do_odebrania_czysta` – ilość energii gotowa do pobrania w skali 1:1 (automatycznie przemnożona przez współczynnik opustu).
* **Automatyczne odliczanie ważności:** W momencie przełomu miesięcy integracja samoczynnie resetuje licznik sprzed roku, odtwarzając 12-miesięczny cykl ważności energii prosumenckiej.

## Instalacja

### Metoda 1: Przez HACS (Zalecana)

1. Upewnij się, że masz zainstalowany komponent **HACS** w swoim Home Assistant.
2. Przejdź do zakładki **HACS** -> **Integracje**.
3. Kliknij ikonę trzech kropek w prawym górnym rogu i wybierz **Niestandardowe repozytoria** (Custom repositories).
4. Wklej adres URL swojego repozytorium na GitHubie.
5. Jako kategorię wybierz **Integracja** i kliknij **Dodaj**.
6. Odszukaj **Net Metering Virtual Storage** na liście i kliknij **Pobierz**.
7. Uruchom ponownie Home Assistant.

### Metoda 2: Instalacja ręczna

1. Pobierz zawartość katalogu `custom_components/net_metering_storage/`.
2. Skopiuj ten katalog do wnętrza folderu `custom_components/` w strukturze plików Twojego Home Assistant.
3. Uruchom ponownie Home Assistant.

## Konfiguracja

Po restarcie systemu:
1. Przejdź do: **Ustawienia** -> **Urządzenia oraz usługi** -> **Dodaj integrację**.
2. Wyszukaj **Net Metering Virtual Storage**.
3. **Krok 1:** Wybierz z listy encje zbilansowanego eksportu i importu (w kWh) pochodzące z Twojego licznika lub integracji bilansującej oraz podaj współczynnik opustu (domyślnie `0.8`).
4. **Krok 2:** Wpisz aktualne, surowe wartości pozostałej energii z ostatniej faktury rozliczeniowej osobno dla każdego miesiąca.

## Jak działa algorytm?

1. **Dodawanie energii:** Każdy przyrost na encji zbilansowanego eksportu zwiększa zasoby w bieżącym miesiącu kalendarzowym.
2. **Pobieranie energii:** Każdy przyrost na encji zbilansowanego importu jest przeliczany na jednostki surowe (`import / współczynnik`) i odejmowany od najstarszego dostępnego miesiąca z zapasami.
3. **Wygasanie nadwyżek:** Pierwszego dnia nowego miesiąca system automatycznie czyści dane dla tego konkretnego miesiąca w pamięci podręcznej, ponieważ zmagazynowana w nim rok wcześniej energia utraciła ważność (minęło 12 miesięcy).

## Wsparcie i wkład

Jeśli zauważysz błąd lub chcesz rozbudować integrację o nowe funkcje (np. powiadomienia o zbliżającym się terminie wygaśnięcia energii), śmiało otwieraj zgłoszenie (Issue) lub wysyłaj Pull Request w repozytorium GitHub.
