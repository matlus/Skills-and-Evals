from typing import final


@final
class ScorecardSummaryUnreadableException(Exception):
    """A run folder's scorecard.json is not one this app wrote, so it cannot be compared."""
