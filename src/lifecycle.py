INITIAL_STATUS = "intake"

# Kept deliberately small for this walking skeleton: only the stages the
# system can actually reach today. STORY-008 adds the review/approval
# stages. STORY-009 adds "validated" for a draft whose data accuracy has
# been confirmed post-approval. STORY-010 adds "published" for a
# finalized dashboard made available to stakeholders, and
# "publication_failed" for a publish attempt that didn't succeed.
VALID_STATUSES = (
    "intake",
    "analyzed",
    "analysis_failed",
    "completed",
    "in_review",
    "changes_requested",
    "approved",
    "validated",
    "published",
    "publication_failed",
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
    # STORY-009: an approved draft is validated for data accuracy before
    # finalization. A validation failure reuses the existing
    # changes_requested correction loop rather than a parallel one.
    "approved": ("validated", "changes_requested"),
    "completed": (),
    # STORY-010: a validated (finalized) dashboard is published to
    # stakeholders. A failed publish attempt can be retried once the
    # underlying issue is fixed, rather than looping back through
    # review/validation again -- the draft itself wasn't the problem.
    "validated": ("published", "publication_failed"),
    "publication_failed": ("published", "publication_failed"),
    "published": (),
}


class InvalidTransitionError(ValueError):
    """Raised when a status change isn't a legal lifecycle transition."""
