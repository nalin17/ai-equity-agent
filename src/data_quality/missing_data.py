"""Missing Data Intelligence (architecture Section 4C).

"Missing" is not one state. Every absent value must say WHY it is absent.
This is the single place the missing-data classes are defined; every other
module imports them from here (architecture 40D: vocabularies are defined
once).
"""
from enum import StrEnum


class MissingClass(StrEnum):
    NOT_APPLICABLE = "not_applicable"            # concept does not apply (inventory for a bank)
    NOT_YET_RELEASED = "not_yet_released"        # period exists, disclosure not yet due
    NOT_DISCLOSED = "not_disclosed"              # due, company chose not to disclose
    EXTRACTION_FAILURE = "extraction_failure"    # present in source, we failed to read it
    SOURCE_CONFLICT = "source_conflict"          # sources disagree, unresolved
    STRUCTURALLY_ABSENT = "structurally_absent"  # never existed (pre-listing)


class MissingDataError(Exception):
    """A value/missing-class combination breaks the Section 4C rules."""


def check_value(value, missing_class=None):
    """Every value is either present, or absent WITH a class - never a bare null.

    Returns (value, missing_class) ready to store.
    """
    if value is None:
        if missing_class is None:
            raise MissingDataError("A null value must carry a missing-data class (4C rule 1)")
        return None, MissingClass(missing_class)
    if missing_class is not None:
        raise MissingDataError("A value that is present cannot also have a missing-data class")
    return value, None


def check_reclassification(old_class, new_class, evidence=None):
    """Changing why a value is missing needs a reason.

    4C rule 3: extraction_failure never silently becomes not_disclosed - a bug
    in our parser must not be recorded as a decision by the company.
    """
    old_class, new_class = MissingClass(old_class), MissingClass(new_class)
    if old_class == new_class:
        return new_class
    if not evidence or not str(evidence).strip():
        raise MissingDataError(f"Reclassifying {old_class} -> {new_class} requires written evidence")
    return new_class


def check_imputable(missing_class):
    """4C rule 2: non-disclosure is evidence, so it is never filled in.

    Conflicts and extraction failures are defects to fix, not gaps to fill.
    """
    missing_class = MissingClass(missing_class)
    if missing_class in {
        MissingClass.NOT_DISCLOSED,
        MissingClass.SOURCE_CONFLICT,
        MissingClass.EXTRACTION_FAILURE,
    }:
        raise MissingDataError(f"Values missing as '{missing_class}' may never be imputed")
    return missing_class
