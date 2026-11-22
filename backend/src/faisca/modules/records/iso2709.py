"""ISO 2709 (the MARC exchange file format) for UNIMARC records, in UTF-8.

pymarc's own `as_marc()` writes UTF-8 only after setting leader/09 to "a",
which is MARC21's flag for Unicode. In UNIMARC that position is undefined and
the character set is declared in field 100 instead, so the file is written
here, by the standard, with the leader left as the record has it.
"""

from collections.abc import Iterable

from pymarc import Field, Record

FIELD_TERMINATOR = b"\x1e"
RECORD_TERMINATOR = b"\x1d"
SUBFIELD_DELIMITER = b"\x1f"
LEADER_LENGTH = 24
DIRECTORY_ENTRY_LENGTH = 12


def record_to_iso2709(record: Record) -> bytes:
    """One record in ISO 2709: leader, directory, then the fields' data."""
    field_bodies = [_field_body(field) for field in record.fields]
    directory = bytearray()
    offset = 0
    for field, body in zip(record.fields, field_bodies, strict=True):
        # Directory entry: tag (3), field length (4), start position (5).
        directory += f"{field.tag:0>3}{len(body):04d}{offset:05d}".encode("ascii")
        offset += len(body)
    directory += FIELD_TERMINATOR

    base_address = LEADER_LENGTH + len(directory)
    record_length = base_address + offset + len(RECORD_TERMINATOR)
    leader = _leader_with_lengths(str(record.leader), record_length, base_address)
    return leader.encode("ascii") + bytes(directory) + b"".join(field_bodies) + RECORD_TERMINATOR


def records_to_iso2709(records: Iterable[Record]) -> bytes:
    """Several records in one file: ISO 2709 records are simply written one after another."""
    return b"".join(record_to_iso2709(record) for record in records)


def _field_body(field: Field) -> bytes:
    if field.is_control_field():
        return (field.data or "").encode("utf-8") + FIELD_TERMINATOR
    body = (field.indicator1 + field.indicator2).encode("utf-8")
    for subfield in field.subfields:
        body += SUBFIELD_DELIMITER + subfield.code.encode("utf-8") + subfield.value.encode("utf-8")
    return body + FIELD_TERMINATOR


def _leader_with_lengths(leader: str, record_length: int, base_address: int) -> str:
    leader = leader.ljust(LEADER_LENGTH)[:LEADER_LENGTH]
    # Positions 10-11 (indicator and subfield-code counts) and 20-23 (the
    # directory entry map) are fixed by ISO 2709 for every MARC format.
    return f"{record_length:05d}{leader[5:10]}22{base_address:05d}{leader[17:20]}450 "
