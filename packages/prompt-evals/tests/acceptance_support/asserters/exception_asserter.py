from collections.abc import Mapping

from prompt_evals import PromptEvalsBaseException


class ExceptionAsserter:
    """Checks the four layers of an exception: precise type, message phrases, and contextual data (which carries its metadata).

    `unexpected_message_phrases` are phrases the message must not contain, such as a remedy that belongs to another failure.
    `expected_contextual_entry_names` are entries whose value the test cannot know in advance, such as the operating
    system's error text or a process id; only their presence is checked.
    """

    @staticmethod
    def assert_expected_and_actual_are_equal(
        *,
        expected_exception_type: type[PromptEvalsBaseException],
        expected_message_phrases: tuple[str, ...],
        expected_contextual_entries_by_name: Mapping[str, object],
        actual_prompt_evals_base_exception: PromptEvalsBaseException,
        unexpected_message_phrases: tuple[str, ...] = (),
        expected_contextual_entry_names: tuple[str, ...] = (),
    ) -> None:
        mismatches: list[str] = []
        if type(actual_prompt_evals_base_exception) is not expected_exception_type:
            mismatches.append(f"type: expected {expected_exception_type.__name__}, actual {type(actual_prompt_evals_base_exception).__name__}")
        mismatches.extend(
            f"message: expected to mention {message_phrase!r}, actual {actual_prompt_evals_base_exception.message!r}"
            for message_phrase in expected_message_phrases
            if message_phrase not in actual_prompt_evals_base_exception.message
        )
        mismatches.extend(
            f"message: expected not to mention {message_phrase!r}, actual {actual_prompt_evals_base_exception.message!r}"
            for message_phrase in unexpected_message_phrases
            if message_phrase in actual_prompt_evals_base_exception.message
        )
        actual_contextual_data_by_name: Mapping[str, object] = actual_prompt_evals_base_exception.contextual_data_by_name
        entry_name: str
        expected_value: object
        for entry_name, expected_value in expected_contextual_entries_by_name.items():
            if actual_contextual_data_by_name.get(entry_name) != expected_value:
                mismatches.append(f"context {entry_name}: expected {expected_value!r}, actual {actual_contextual_data_by_name.get(entry_name)!r}")
        mismatches.extend(
            f"context {expected_entry_name}: expected the entry to be present, actual entries {sorted(actual_contextual_data_by_name)}"
            for expected_entry_name in expected_contextual_entry_names
            if expected_entry_name not in actual_contextual_data_by_name
        )
        assert not mismatches, f"Exception mismatches ({len(mismatches)}):\n" + "\n".join(mismatches)
