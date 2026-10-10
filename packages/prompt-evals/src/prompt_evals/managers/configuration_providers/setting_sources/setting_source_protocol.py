from typing import Protocol


class SettingSourceProtocol(Protocol):
    def read_setting_value(self, setting_name: str) -> str | None: ...
