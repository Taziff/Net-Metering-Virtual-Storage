import logging
from datetime import datetime
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN, CONF_SOURCE_EXPORT, CONF_SOURCE_IMPORT, CONF_FACTOR

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Tworzenie i dodawanie encji sensorów na podstawie konfiguracji GUI."""
    config = entry.data
    
    sensor_raw = VirtualStorageSensor(hass, entry, config, is_raw=True)
    sensor_net = VirtualStorageSensor(hass, entry, config, is_raw=False)
    sensor_alert = EndangeredPackageSensor(hass, entry, config, sensor_net)
    
    async_add_entities([sensor_raw, sensor_net, sensor_alert])

class VirtualStorageSensor(SensorEntity, RestoreEntity):
    """Implementacja uniwersalnego sensora magazynu energii odpornego na restarty."""
    
    def __init__(self, hass, entry, config, is_raw):
        self.hass = hass
        self._entry = entry
        self._is_raw = is_raw
        self._export_entity = config[CONF_SOURCE_EXPORT]
        self._import_entity = config[CONF_SOURCE_IMPORT]
        self._factor = config[CONF_FACTOR]
        
        self._months_storage = {int(k): float(v) for k, v in config["initial_months"].items()}
        self._current_tracked_month = datetime.now().month
        
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
        """Przywracanie danych z bazy HA po restarcie oraz rejestracja nasłuchiwania zmian."""
        old_state = await self.async_get_last_state()
        if old_state is not None:
            try:
                months_names = {
                    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień", 
                    5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień", 
                    9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
                }
                
                for m, name in months_names.items():
                    if name in old_state.attributes:
                        val_str = old_state.attributes[name].replace(" kWh", "")
                        if not self._is_raw:
                            self._months_storage[m] = float(val_str) / self._factor
                        else:
                            self._months_storage[m] = float(val_str)
                
                _LOGGER.info("Wirtualny Magazyn (%s): Pomyślnie przywrócono stany miesięcy po restarcie.", self._attr_name)
            except Exception as e:
                _LOGGER.error("Wirtualny Magazyn: Błąd podczas przywracania stanów miesięcy: %s", e)

        @callback
        def _state_changed_listener(event):
            self.async_update_values()

        self.async_on_remove(async_track_state_change_event(
            self.hass, [self._export_entity, self._import_entity], _state_changed_listener
        ))
        
        exp_state = self.hass.states.get(self._export_entity)
        imp_state = self.hass.states.get(self._import_entity)
        
        if exp_state and exp_state.state not in (None, "unknown", "unavailable"):
            try: self._last_export = float(exp_state.state)
            except ValueError: pass
                
        if imp_state and imp_state.state not in (None, "unknown", "unavailable"):
            try: self._last_import = float(imp_state.state)
            except ValueError: pass
                
        self.async_write_ha_state()

    def async_update_values(self):
        """Logika obliczeniowa magazynu z uwzględnieniem FIFO oraz resetu rocznego."""
        exp_state = self.hass.states.get(self._export_entity)
        imp_state = self.hass.states.get(self._import_entity)
        
        if not exp_state or not imp_state: return
        if exp_state.state in (None, "unknown", "unavailable") or imp_state.state in (None, "unknown", "unavailable"): return

        try:
            current_export = float(exp_state.state)
            current_import = float(imp_state.state)
        except ValueError: return

        now_month = datetime.now().month

        if now_month != self._current_tracked_month:
            self._months_storage[now_month] = 0.0
            self._current_tracked_month = now_month

        if self._last_export is not None and self._last_import is not None:
            delta_export = current_export - self._last_export
            delta_import = current_import - self._last_import
            
            if delta_export > 0:
                self._months_storage[now_month] += delta_export

            if delta_import > 0:
                pobor_surowy = delta_import / self._factor
                order = list(range(now_month + 1, 13)) + list(range(1, now_month + 1))
                for m in order:
                    if self._months_storage[m] >= pobor_surowy:
                        self._months_storage[m] -= pobor_surowy
                        pobor_surowy = 0.0
                        break
                    else:
                        pobor_surowy -= self._months_storage[m]
                        self._months_storage[m] = 0.0
                    
                    if pobor_surowy <= 0.0:
                        self._state_value = round(val * self._factor, 2)
                        self._endangered_month_name = months_names[m]
                        found = True
                        break
                
        if not found:
            self._state_value = 0.0
            self._endangered_month_name = "Brak"
            
        self.async_write_ha_state()

    @property
    def state(self):
        """Zwraca surową liczbę kWh potrzebną do wykresu liniowego."""
        return self._state_value

    @property
    def extra_state_attributes(self):
        """Zapisuje nazwę zagrożonego miesiąca w atrybutach tekstowych."""
        return {"zagrozony_miesiac": self._endangered_month_name}
