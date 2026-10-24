import logging
from datetime import datetime
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN, CONF_SOURCE_EXPORT, CONF_SOURCE_IMPORT, CONF_FACTOR

_LOGGER = logging.getLogger(__name__)
M_NAMES = {1:"Styczeń", 2:"Luty", 3:"Marzec", 4:"Kwiecień", 5:"Maj", 6:"Czerwiec", 7:"Lipiec", 8:"Sierpień", 9:"Wrzesień", 10:"Październik", 11:"Listopad", 12:"Grudzień"}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    config = entry.data
    sensor_raw = VirtualStorageSensor(hass, entry, config, is_raw=True)
    sensor_net = VirtualStorageSensor(hass, entry, config, is_raw=False)
    sensor_alert = EndangeredPackageSensor(hass, entry, config, sensor_net)
    async_add_entities([sensor_raw, sensor_net, sensor_alert])

class VirtualStorageSensor(SensorEntity, RestoreEntity):
    def __init__(self, hass, entry, config, is_raw):
        self.hass = hass
        self._is_raw = is_raw
        self._export_entity = config[CONF_SOURCE_EXPORT]
        self._import_entity = config[CONF_SOURCE_IMPORT]
        self._factor = config[CONF_FACTOR]
        self._months_storage = {int(k): float(v) for k, v in config["initial_months"].items()}
        self._current_tracked_month = datetime.now().month
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_unit_of_measurement = "kWh"
        self._attr_name = "Wirtualny Magazyn - Energia Wprowadzona" if is_raw else "Wirtualny Magazyn - Do Odebrania (Czysta)"
        self._attr_unique_id = f"{entry.entry_id}_storage_raw" if is_raw else f"{entry.entry_id}_storage_net"
        self._last_export, self._last_import = None, None

    async def async_added_to_hass(self):
        old_state = await self.async_get_last_state()
        if old_state is not None:
            for m, name in M_NAMES.items():
                if name in old_state.attributes:
                    val = float(old_state.attributes[name].replace(" kWh", ""))
                    self._months_storage[m] = val if self._is_raw else val / self._factor
        
        @callback
        def _listener(event): self.async_update_values()
        self.async_on_remove(async_track_state_change_event(self.hass, [self._export_entity, self._import_entity], _listener))
        
        exp, imp = self.hass.states.get(self._export_entity), self.hass.states.get(self._import_entity)
        if exp and exp.state not in (None, "unknown", "unavailable"): self._last_export = float(exp.state)
        if imp and imp.state not in (None, "unknown", "unavailable"): self._last_import = float(imp.state)
        self.async_write_ha_state()

    def async_update_values(self):
        exp, imp = self.hass.states.get(self._export_entity), self.hass.states.get(self._import_entity)
        if not exp or not imp or exp.state in (None, "unknown", "unavailable") or imp.state in (None, "unknown", "unavailable"): return
        try:
            cur_exp, cur_imp = float(exp.state), float(imp.state)
        except ValueError: return

        now_m = datetime.now().month
        if now_m != self._current_tracked_month:
            self._months_storage[now_m] = 0.0
            self._current_tracked_month = now_m

        if self._last_export is not None and self._last_import is not None:
            if cur_exp > self._last_export: self._months_storage[now_m] += (cur_exp - self._last_export)
            if cur_imp > self._last_import:
                pobor = (cur_imp - self._last_import) / self._factor
                for m in list(range(now_m + 1, 13)) + list(range(1, now_m + 1)):
                    if self._months_storage[m] >= pobor:
                        self._months_storage[m] -= pobor
                        break
                    pobor -= self._months_storage[m]
                    self._months_storage[m] = 0.0

        self._last_export, self._last_import = cur_exp, cur_imp
        self.async_write_ha_state()

    @property
    def state(self):
        return round(sum(self._months_storage.values()), 2) if self._is_raw else round(sum(self._months_storage.values()) * self._factor, 2)

    @property
    def extra_state_attributes(self):
        mult = 1.0 if self._is_raw else self._factor
        return {M_NAMES[m]: f"{round(val * mult, 2)} kWh" for m, val in self._months_storage.items()}

    @property
    def months_data(self): return self._months_storage


class EndangeredPackageSensor(SensorEntity):
    def __init__(self, hass, entry, config, parent_sensor):
        self.hass = hass
        self._parent = parent_sensor
        self._factor = config[CONF_FACTOR]
        self._attr_name = "Wirtualny Magazyn - Najbardziej Zagrożona Paczka"
        self._attr_unique_id = f"{entry.entry_id}_endangered_package"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_unit_of_measurement = "kWh"
        self._attr_icon = "mdi:alert-circle-outline"
        self._state_value, self._month_name = 0.0, "Brak"

    async def async_added_to_hass(self):
        @callback
        def _listener(event): self.async_update_alert()
        self.async_on_remove(async_track_state_change_event(self.hass, [self._parent.entity_id], _listener))
        self.async_update_alert()

    def async_update_alert(self):
        now_m = datetime.now().month
        m_dict = self._parent.months_data
        for m in list(range(now_m + 1, 13)) + list(range(1, now_m + 1)):
            if m_dict.get(m, 0.0) > 0.0:
                self._state_value = round(m_dict[m] * self._factor, 2)
                self._month_name = M_NAMES[m] # TUTAJ JEST PRZYPISANIE W NOWEJ KLASIE
                self.async_write_ha_state()
                return
        self._state_value, self._month_name = 0.0, "Brak"
        self.async_write_ha_state()

    @property
    def state(self): return self._state_value

    @property
    def extra_state_attributes(self): return {"zagrozony_miesiac": self._month_name}
