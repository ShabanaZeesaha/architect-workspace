INITIAL_STATUS = "intake"

# Kept deliberately small for this walking skeleton: only the stages the
# system can actually reach today, plus "completed" for REQ-008's "intake to
# completion" lifecycle. Approval/review-specific stages belong to the story
# that builds that workflow, not this one.
VALID_STATUSES = ("intake", "analyzed", "analysis_failed", "completed")

# Which status changes are legal, keyed by current status. A status
# transitioning to itself is always allowed (handled separately as an
# idempotent no-op) and is not listed here.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "intake": ("analyzed", "analysis_failed"),
    "analysis_failed": ("intake",),
    "analyzed": ("completed",),
    "completed": (),
}


class InvalidTransitionError(ValueError):
    """Raised when a status change isn't a legal lifecycle transition."""
