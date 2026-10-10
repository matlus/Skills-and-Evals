from collections.abc import Mapping


class SettingSourceStub:
    """Answers settings from the test's own values only, so the developer's environment cannot change a test's outcome."""

    def __init__(self, setting_value_by_setting_name: Mapping[str, str]) -> None:
        self._setting_value_by_setting_name: Mapping[str, str] = setting_value_by_setting_name

    def read_setting_value(self, setting_name: str) -> str | None:
        return self._setting_value_by_setting_name.get(setting_name)
