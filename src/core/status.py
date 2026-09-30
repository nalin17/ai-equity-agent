"""Capability status vocabulary (architecture 2A) and stage acceptance records (40).

Every stage, feature, contract and capability carries exactly one status.
This is the single place the vocabulary is defined.

A stage acceptance states both halves (architecture 40, 40D.1, criterion 69):
what is proven, and what is NOT claimed. Every not-claimed entry must be
exactly False - omission would read as completeness.
"""
import re
from pathlib import Path

import yaml

from core.config import PROJECT_ROOT

STAGES_DIR = PROJECT_ROOT / "stages"

FIXED_STATUSES = {
    "CLOSED",
    "PROTOTYPE",
    "SCAFFOLD",
    "HELD",
    "BLOCKED",
    "FAIL_CLOSED",
    "DEFERRED",
    "AVAILABILITY_REVIEW",
}
ACCEPTED_BASELINE = re.compile(r"^ACCEPTED_[A-Z0-9]+(_[A-Z0-9]+)*_BASELINE$")

REQUIRED_KEYS = ("stage", "status", "architecture", "proven", "not_claimed", "negative_assertions")


class AcceptanceError(Exception):
    """A stage acceptance record breaks the architecture 2A / 40 rules."""


def is_valid_status(status):
    return status in FIXED_STATUSES or bool(ACCEPTED_BASELINE.match(str(status)))


def validate_acceptance(record, name="record"):
    missing = [k for k in REQUIRED_KEYS if k not in record]
    if missing:
        raise AcceptanceError(f"{name}: missing keys {missing}")
    if not is_valid_status(record["status"]):
        raise AcceptanceError(f"{name}: status {record['status']!r} is not in the 2A vocabulary")
    if not record["proven"]:
        raise AcceptanceError(f"{name}: 'proven' must list what was proven")
    for section in ("not_claimed", "negative_assertions"):
        entries = record[section]
        if not isinstance(entries, dict) or not entries:
            raise AcceptanceError(f"{name}: '{section}' must be a non-empty list of items: False")
        wrong = [k for k, v in entries.items() if v is not False]
        if wrong:
            raise AcceptanceError(f"{name}: '{section}' entries must be exactly False: {wrong}")
    return record


def load_acceptance_records(folder=STAGES_DIR):
    records = {}
    for path in sorted(Path(folder).glob("*_acceptance.yaml")):
        with open(path, encoding="utf-8-sig") as f:
            records[path.name] = validate_acceptance(yaml.safe_load(f) or {}, path.name)
    return records
