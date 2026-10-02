"""Architecture rules enforced by reading the source code (architecture 40D).

These tests do not run the system. They read the code and fail if a rule
that would otherwise be broken silently has been broken.
"""
import re

from core.config import PROJECT_ROOT
from data_quality.missing_data import MissingClass

SRC = PROJECT_ROOT / "src"


def source_files():
    return [p for p in SRC.rglob("*.py")]


def test_bare_review_token_is_never_used():
    # 5B.3: AVAILABILITY_REVIEW and OUTPUT_REVIEW are different states;
    # the bare token REVIEW is prohibited.
    pattern = re.compile(r"(?<![A-Z_])REVIEW(?![A-Z_])")
    offenders = [str(p) for p in source_files() if pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


def test_missing_data_classes_are_defined_in_one_place():
    # 40D: vocabularies are defined once and imported, never restated.
    home = SRC / "data_quality" / "missing_data.py"
    for path in source_files():
        if path == home:
            continue
        text = path.read_text(encoding="utf-8")
        for cls in MissingClass:
            assert f'"{cls.value}"' not in text and f"'{cls.value}'" not in text, (
                f"{path} restates missing-data class {cls.value!r}; import MissingClass instead"
            )


def test_dates_are_parsed_only_by_core_dates():
    # Found in Stage 6: date.fromisoformat() accepts '20240101' and '2024-W01-1',
    # which sort wrongly as text. Only core/dates.py may call it (40D rule 3).
    home = SRC / "core" / "dates.py"
    pattern = re.compile(r"\bdate\.fromisoformat\(")
    offenders = [str(p) for p in source_files()
                 if p != home and pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []
