from ....protocol import ErrorResponse


class FailedUpdateResponse(ErrorResponse):
    """Represent an update rejected by the Envelope v11 mapper."""

