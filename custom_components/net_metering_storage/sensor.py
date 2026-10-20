import logging
from datetime import datetime
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN, CONF_SOURCE_EXPORT, CONF_SOURCE_IMPORT, CONF_FACTOR, CONF_INITIAL_BALANCE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Tworzenie i dodawanie encji sensorów."""
    config = entry.data
    
    sensor_raw = VirtualStorageSensor(hass, config, is_raw=True)
    sensor_net = VirtualStorageSensor(hass, config, is_raw=False)
    
    async_add_entities([sensor_raw, sensor_net])

class VirtualStorageSensor(SensorEntity):
    """Implementacja sensora wirtualnego magazynu."""
    
    def __init__(self, hass, config, is_raw):
        self.hass = hass
        self._is_raw = is_raw
        self._export_entity = config[CONF_SOURCE_EXPORT]
        self._import_entity = config[CONF_SOURCE_IMPORT]
        self._factor = config[CONF_FACTOR]
        
        # Inicjalizacja magazynu miesięcznego (12 miesięcy)
        self._months_storage = {i: 0.0 for i in range(1, 13)}
        
        # Wpisanie wartości początkowej z faktury do bieżącego miesiąca jako punkt startowy
        current_month = datetime.now().month
        self._months_storage[current_month] = config[CONF_INITIAL_BALANCE]
        
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_unit_of_measurement = "kWh"
        
        if is_raw:
            self._attr_name = "Wirtualny Magazyn - Energia Wprowadzona"
            self._attr_unique_id = f"{entry.entry_id}_storage_raw"
        else:
            self._attr_name = "Wirtualny Magazyn - Do Odebrania (Czysta)"
            self._attr_unique_id = f"{entry.entry_id}_storage_net"

        self._last_export = None
        self._last_import = None

    async def async_added_to_hass(self):
        """Rejestracja nasłuchiwania zmian na licznikach fizycznych."""
        @callback
        def _state_changed_listener(event):
            self.async_update_values()

        self.async_on_remove(async_track_state_change_event(self.hass, [self._export_entity, self._import_entity], _state_changed_listener))
        
        # Pobranie stanów początkowych
        exp_state = self.hass.states.get(self._export_entity)
        imp_state = self.hass.states.get(self._import_entity)
        if exp_state: self._last_export = float(exp_state.state)
        if imp_state: self._last_import = float(imp_state.state)

    def async_update_values(self):
        """Przeliczanie stanu magazynu na podstawie przyrostu liczników."""
        exp_state = self.hass.states.get(self._export_entity)
        imp_state = self.hass.states.get(self._import_entity)
        
        if not exp_state or not imp_state:
            return

        try:
            current_export = float(exp_state.state)
            current_import = float(imp_state.state)
        except ValueError:
            return

        if self._last_export is not None and self._last_import is not None:
            delta_export = current_export - self._last_export
            delta_import = current_import - self._last_import
            
            current_month = datetime.now().month
            
            # 1. Dodaj bieżący eksport do aktualnego miesiąca
            if delta_export > 0:
                self._months_storage[current_month] += delta_export

            # 2. Odejmij import (zużycie) z zachowaniem zasady FIFO (od najstarszego miesiąca)
            if delta_import > 0:
                # Koszt poboru z magazynu surowego (1 kWh pobrany = 1 / współczynnik w magazynie surowym)
                pobor_surowy = delta_import / self._factor
                
                # Przechodzimy przez miesiące zaczynając od kolejnego po bieżącym (najstarszego w cyklu 12m)
                order = list(range(current_month + 1, 13)) + list(range(1, current_month + 1))
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

    @property
    def state(self):
        """Zwraca sumaryczną wartość magazynu."""
        total_raw = sum(self._months_storage.values())
        if self._is_raw:
            return round(total_raw, 2)
        return round(total_raw * self._factor, 2)

    @property
    def extra_state_attributes(self):
        """Rozbicie wartości na poszczególne miesiące widoczne w szczegółach sensora."""
        months_names = {
            1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień", 
            5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień", 
            9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
        }
        
        attributes = {}
        multiplier = 1.0 if self._is_raw else self._factor
        
        for m, val in self._months_storage.items():
            attributes[months_names[m]] = f"{round(val * multiplier, 2)} kWh"
            
        return attributes
