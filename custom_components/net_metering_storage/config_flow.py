import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import selector
from .const import DOMAIN, CONF_SOURCE_EXPORT, CONF_SOURCE_IMPORT, CONF_FACTOR

class NetMeteringStorageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Obsługa dwuetapowego okienka konfiguracji."""
    VERSION = 1

    def __init__(self):
        """Inicjalizacja przepływu konfiguracji."""
        self.init_data = {}

    async def async_step_user(self, user_input=None):
        """Krok 1: Wybór encji i współczynnika."""
        if user_input is not None:
            self.init_data.update(user_input)
            # POPRAWKA: Przejście do kolejnego kroku musi być wywołane przez przekazanie pustego słownika do funkcji obsługującej krok
            return await self.async_step_months(user_input=None)

        data_schema = vol.Schema({
            vol.Required(CONF_SOURCE_EXPORT): selector({"entity": {"domain": "sensor", "device_class": "energy"}}),
            vol.Required(CONF_SOURCE_IMPORT): selector({"entity": {"domain": "sensor", "device_class": "energy"}}),
            vol.Required(CONF_FACTOR, default=0.8): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1.0)),
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)

    async def async_step_months(self, user_input=None):
        """Krok 2: Wprowadzenie wartości początkowych dla każdego miesiąca."""
        if user_input is not None:
            # Mapujemy wprowadzone pola tekstowe m1-m12 na strukturę słownika w danych integracji
            self.init_data["initial_months"] = {int(k[1:]): float(v) for k, v in user_input.items()}
            return self.async_create_entry(title="Wirtualny Magazyn Energii", data=self.init_data)

        # Tworzymy formularz z 12 polami (każde domyślnie ustawione na 0.0)
        months_schema = vol.Schema({
            vol.Required(f"m{i}", default=0.0): vol.Coerce(float) for i in range(1, 13)
        })

        return self.async_show_form(step_id="months", data_schema=months_schema)
