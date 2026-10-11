from collections.abc import Mapping

from prompt_evals import PromptEvalsBaseException


class ExceptionAsserter:
    """Checks the four layers of an exception: precise type, message phrases, and contextual data (which carries its metadata)."""

    @staticmethod
    def assert_expected_and_actual_are_equal(
        *,
        expected_exception_type: type[PromptEvalsBaseException],
        expected_message_phrases: tuple[str, ...],
        expected_contextual_entries_by_name: Mapping[str, object],
        actual_exception: PromptEvalsBaseException,
    ) -> None:
        mismatches: list[str] = []
        if type(actual_exception) is not expected_exception_type:
            mismatches.append(f"type: expected {expected_exception_type.__name__}, actual {type(actual_exception).__name__}")
        mismatches.extend(
            f"message: expected to mention {message_phrase!r}, actual {actual_exception.message!r}"
            for message_phrase in expected_message_phrases
            if message_phrase not in actual_exception.message
        )
        actual_contextual_data_by_name: Mapping[str, object] = actual_exception.contextual_data_by_name
        entry_name: str
        expected_value: object
        for entry_name, expected_value in expected_contextual_entries_by_name.items():
            if actual_contextual_data_by_name.get(entry_name) != expected_value:
                mismatches.append(f"context {entry_name}: expected {expected_value!r}, actual {actual_contextual_data_by_name.get(entry_name)!r}")
        assert not mismatches, f"Exception mismatches ({len(mismatches)}):\n" + "\n".join(mismatches)
