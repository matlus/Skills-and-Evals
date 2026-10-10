import os
from typing import final


@final
class EnvironmentSettingSource:
    """Reads settings from the process environment, the only place the library touches it."""

    def read_setting_value(self, setting_name: str) -> str | None:
        return os.environ.get(setting_name)
