import secrets
import string


class RandomDataGenerator:
    """Values whose exact content does not matter to a test, so the test cannot depend on them by accident."""

    @staticmethod
    def create_random_word(length: int = 8) -> str:
        return "".join(secrets.choice(string.ascii_lowercase) for _ in range(length))

    @staticmethod
    def create_random_sentence(word_count: int = 6) -> str:
        return " ".join(RandomDataGenerator.create_random_word() for _ in range(word_count)).capitalize() + "."

    @staticmethod
    def create_random_amount_text() -> str:
        return f"{secrets.randbelow(9_000) + 100}.{secrets.randbelow(100):02d}"
