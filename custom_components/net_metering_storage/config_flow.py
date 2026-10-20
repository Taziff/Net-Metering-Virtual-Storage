import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import selector
from .const import DOMAIN, CONF_SOURCE_EXPORT, CONF_SOURCE_IMPORT, CONF_FACTOR

class NetMeteringStorageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Obsługa dwuetapowego okienka konfiguracji bez utraty stanu w pamięci."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Krok 1: Wybór encji i współczynnika."""
        if user_input is not None:
            # Przekazujemy zebrane dane z kroku 1 bezpośrednio jako kontekst (user_input) do kroku 2
            return await self.async_step_months(user_input=None, step_1_data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_SOURCE_EXPORT): selector({"entity": {"domain": "sensor", "device_class": "energy"}}),
            vol.Required(CONF_SOURCE_IMPORT): selector({"entity": {"domain": "sensor", "device_class": "energy"}}),
            vol.Required(CONF_FACTOR, default=0.8): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1.0)),
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)

    async def async_step_months(self, user_input=None, step_1_data=None):
        """Krok 2: Wprowadzenie wartości początkowych dla każdego miesiąca."""
        # Przy pierwszym wywołaniu kroku 2, zapisujemy dane z kroku 1 w wewnętrznym kontekście przepływu HA
        if step_1_data is not None:
            self._step_1_data = step_1_data

        if user_input is not None:
            # Łączymy dane z kroku 1 (z licznika) oraz kroku 2 (wpisane miesiące)
            final_data = {}
            if hasattr(self, "_step_1_data"):
                final_data.update(self._step_1_data)
                
            final_data["initial_months"] = {int(k[1:]): float(v) for k, v in user_input.items()}
            return self.async_create_entry(title="Wirtualny Magazyn Energii", data=final_data)

        # Wyświetlamy formularz z 12 polami miesięcy
        months_schema = vol.Schema({
            vol.Required(f"m{i}", default=0.0): vol.Coerce(float) for i in range(1, 13)
        })

        return self.async_show_form(step_id="months", data_schema=months_schema)
