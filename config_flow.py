import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import selector
from .const import DOMAIN, CONF_SOURCE_EXPORT, CONF_SOURCE_IMPORT, CONF_FACTOR, CONF_INITIAL_BALANCE

class NetMeteringStorageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Obsługa okienka konfiguracji w interfejsie HA."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Wirtualny Magazyn Energii", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_SOURCE_EXPORT): selector({"entity": {"domain": "sensor", "device_class": "energy"}}),
            vol.Required(CONF_SOURCE_IMPORT): selector({"entity": {"domain": "sensor", "device_class": "energy"}}),
            vol.Required(CONF_FACTOR, default=0.8): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1.0)),
            vol.Required(CONF_INITIAL_BALANCE, default=0.0): vol.Coerce(float),
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)
