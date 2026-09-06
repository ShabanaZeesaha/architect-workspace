INITIAL_STATUS = "intake"

# Kept deliberately small for this walking skeleton: only the stages the
# system can actually reach today. STORY-008 adds the review/approval
# stages; finalization-specific stages beyond "approved" belong to
# STORY-009, not this one.
VALID_STATUSES = (
    "intake",
    "analyzed",
    "analysis_failed",
    "completed",
    "in_review",
    "changes_requested",
    "approved",
)

# Which status changes are legal, keyed by current status. A status
# transitioning to itself is always allowed (handled separately as an
# idempotent no-op) and is not listed here.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "intake": ("analyzed", "analysis_failed"),
    "analysis_failed": ("intake",),
    "analyzed": ("completed", "in_review"),
    "in_review": ("approved", "changes_requested"),
    "changes_requested": ("in_review",),
    "approved": (),
    "completed": (),
}


class InvalidTransitionError(ValueError):
    """Raised when a status change isn't a legal lifecycle transition."""
