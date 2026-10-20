import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import selector
from .const import DOMAIN, CONF_SOURCE_EXPORT, CONF_SOURCE_IMPORT, CONF_FACTOR

class NetMeteringStorageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Obsługa dwuetapowego okienka konfiguracji."""
    VERSION = 1

        def __init__(self, hass, config, is_raw):
        # ... (poprzedni kod inicjalizacji bez zmian) ...
        self._factor = config[CONF_FACTOR]
        
        # Pobieramy dokładne dane wpisane przez użytkownika dla każdego miesiąca z osobna
        self._months_storage = config["initial_months"].copy()
        
        # Zapisujemy jaki jest miesiąc w momencie uruchomienia integracji
        self._current_tracked_month = datetime.now().month
        # ... (reszta kodu __init__ bez zmian) ...

    def async_update_values(self):
        """Przeliczanie stanu magazynu z automatycznym resetem miesięcy."""
        exp_state = self.hass.states.get(self._export_entity)
        imp_state = self.hass.states.get(self._import_entity)
        
        if not exp_state or not imp_state:
            return

        try:
            current_export = float(exp_state.state)
            current_import = float(imp_state.state)
        except ValueError:
            return

        now_month = datetime.now().month

        # --- TWÓJ POMYSŁ: Automatyczne nadpisywanie miesiąca po roku ---
        if now_month != self._current_tracked_month:
            # Miesiąc właśnie się zmienił! Nadpisujemy (zerujemy) dane tego nowego miesiąca, 
            # ponieważ energia wyprodukowana w nim dokładnie rok temu właśnie bezpowrotnie wygasła.
            self._months_storage[now_month] = 0.0
            self._current_tracked_month = now_month
            _LOGGER.info("Wirtualny Magazyn: Nastąpiła zmiana miesiąca na %s. Resetowanie stanu sprzed roku.", now_month)

        if self._last_export is not None and self._last_import is not None:
            delta_export = current_export - self._last_export
            delta_import = current_import - self._last_import
            
            # 1. Dodaj bieżący eksport do aktualnego miesiąca
            if delta_export > 0:
                self._months_storage[now_month] += delta_export

            # 2. Odejmij import (zużycie) na zasadzie FIFO (od najstarszego)
            if delta_import > 0:
                pobor_surowy = delta_import / self._factor
                
                # Ustalamy kolejność zużywania prądu: od najstarszego pakietu do obecnego miesiąca
                order = list(range(now_month + 1, 13)) + list(range(1, now_month + 1))
                for m in order:
                    if self._months_storage[m] >= pobor_surowy:
                        self._months_storage[m] -= pobor_surowy
                        pobor_surowy = 0
                        break
                    else:
                        pobor_surowy -= self._months_storage[m]
                        self._months_storage[m] = 0.0
                    if pobor_surowy <= 0:
                        break

        self._last_export = current_export
        self._last_import = current_import
        self.async_write_ha_state()
