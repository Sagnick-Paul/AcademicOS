"""Domain exceptions raised by the service layer.

These are deliberately HTTP-agnostic. The FastAPI boundary in
:mod:`app.api.deps` and :mod:`app.api.v1.endpoints.*` is responsible
for translating them into ``HTTPException`` responses with the right
status codes. This keeps services usable from non-HTTP contexts
(workers, CLI tools, tests).
"""


# ---------- Auth (existing) ----------


class EmailAlreadyExistsError(Exception):
    """Raised by ``AuthService.register`` when the email collides."""


class InvalidCredentialsError(Exception):
    """Raised by ``AuthService.authenticate`` when the email does not
    exist or the password does not match. Callers MUST NOT distinguish
    the two cases in their response — that would let an attacker
    enumerate registered emails."""


class InactiveUserError(Exception):
    """Raised by ``AuthService.authenticate`` when the account exists and
    the password is correct, but the account has been deactivated."""


# ---------- Documents ----------


class UnsupportedFileTypeError(Exception):
    """Raised when an upload fails extension / MIME / magic-byte agreement.

    The ``reason`` attribute tells callers whether the failure was due
    to extension (e.g. ".exe"), MIME (wrong Content-Type), or magic
    bytes (Content-Type spoofing). It is for log diagnostics — public
    responses must not leak which check failed.
    """

    def __init__(self, message: str, reason: str = "unknown") -> None:
        super().__init__(message)
        self.reason = reason


class FileTooLargeError(Exception):
    """Raised when an upload exceeds the configured maximum."""

    def __init__(self, actual_size: int, max_size: int) -> None:
        super().__init__(
            f"Upload is {actual_size} bytes; maximum is {max_size} bytes"
        )
        self.actual_size = actual_size
        self.max_size = max_size


class EmptyFileError(Exception):
    """Raised when an upload contains zero bytes."""


class DocumentNotFoundError(Exception):
    """Raised when a document lookup misses — either no such id exists,
    or it exists but belongs to a different user.

    The two cases are deliberately indistinguishable to callers. The
    endpoint translates this to a 404 in both situations so a request
    cannot be used to enumerate document ids belonging to other
    users.
    """

    def __init__(self, document_id: object) -> None:
        super().__init__(f"Document {document_id!r} not found")
        self.document_id = document_id


# ---------- Courses ----------


class CourseNotFoundError(Exception):
    """Raised when a course lookup misses — either no such id exists,
    or it exists but belongs to a different user.

    Mirrors :class:`DocumentNotFoundError`: the two cases are
    deliberately indistinguishable so the endpoint cannot be used to
    enumerate other users' course ids.
    """

    def __init__(self, course_id: object) -> None:
        super().__init__(f"Course {course_id!r} not found")
        self.course_id = course_id


class DuplicateCourseNameError(Exception):
    """Raised when an owner tries to create or rename a course to a name
    they already use for another course.
    """

    def __init__(self, name: str) -> None:
        super().__init__(
            f"You already have a course named {name!r}"
        )
        self.name = name
