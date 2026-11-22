"""Record ids: which target a record came from, and its 001 there, in one URL-safe string.

"porbase.MTIzNDU2" = target "porbase", control number "123456" (base64url).
With the 001 in the id, a record can be fetched again from its target after
the cache has expired. A record without 001 gets "h" + a hash of its content
and can only be served from the cache.
"""

import base64
import binascii
import hashlib
from dataclasses import dataclass

HASH_PREFIX = "h"
CONTROL_NUMBER_PREFIX = "n"


@dataclass(frozen=True)
class ParsedRecordId:
    """A record id taken apart."""

    target_id: str
    control_number: str | None


class InvalidRecordIdError(ValueError):
    """The string is not a record id this app made."""


def make_record_id(target_id: str, control_number: str | None, marcxml: str) -> str:
    """The id for a record from [target_id]."""
    if control_number:
        encoded = (
            base64.urlsafe_b64encode(control_number.encode("utf-8")).decode("ascii").rstrip("=")
        )
        return f"{target_id}.{CONTROL_NUMBER_PREFIX}{encoded}"
    digest = hashlib.sha256(marcxml.encode("utf-8")).hexdigest()[:20]
    return f"{target_id}.{HASH_PREFIX}{digest}"


def parse_record_id(record_id: str) -> ParsedRecordId:
    """The target and (when the id carries one) the control number."""
    target_id, separator, token = record_id.partition(".")
    if not separator or not target_id or len(token) < 2:
        raise InvalidRecordIdError(record_id)
    kind, body = token[0], token[1:]
    if kind == HASH_PREFIX:
        return ParsedRecordId(target_id=target_id, control_number=None)
    if kind != CONTROL_NUMBER_PREFIX:
        raise InvalidRecordIdError(record_id)
    padding = "=" * (-len(body) % 4)
    try:
        # validate=True: without it, characters outside the alphabet are
        # silently dropped and "n%%%" would decode to an empty number.
        decoded = base64.b64decode(body + padding, altchars=b"-_", validate=True)
        control_number = decoded.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as error:
        raise InvalidRecordIdError(record_id) from error
    if not control_number:
        raise InvalidRecordIdError(record_id)
    return ParsedRecordId(target_id=target_id, control_number=control_number)
