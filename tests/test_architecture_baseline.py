"""Architecture control audit, run on every commit (46A rule 4, ADR-007).

Master Architecture v2.2.0 was made from v2.1.1 by insertion only. These tests fail if a
later edit removes or changes any line of v2.1.1 other than the two declared replacements
(the version line and the 'frozen at' line), if an acceptance criterion is renumbered or
dropped, or if the documents that name the governing architecture drift.
"""
import difflib

from core.config import PROJECT_ROOT

DOCS = PROJECT_ROOT / "docs"
OLD = DOCS / "Master_Architecture_v2_1_1_FROZEN.md"
NEW = DOCS / "Master_Architecture_v2_2_0_FROZEN.md"
OLD_TITLE = "## Master Architecture v2.1.1 \u2014 Frozen Institutional Baseline"
NEW_TITLE = "## Master Architecture v2.2.0 \u2014 Frozen Institutional Baseline"
OLD_FROZEN = "5. This document is **frozen at v2.1.1**."
NEW_FROZEN = "5. This document is **frozen at v2.2.0** (previously v2.1.1)."


def lines(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()


def test_v2_2_0_keeps_every_line_of_v2_1_1():
    old, new = lines(OLD), lines(NEW)
    lost = []
    for tag, i1, i2, _, _ in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
        if tag in ("delete", "replace"):
            lost += [line for line in old[i1:i2] if line != OLD_TITLE and not line.startswith(OLD_FROZEN)]
    assert lost == []
    assert NEW_TITLE in new
    assert any(line.startswith(NEW_FROZEN) for line in new)


def test_acceptance_criteria_are_only_ever_added():
    text = "\n".join(lines(NEW))
    section = text[text.index("## 47. Acceptance Criteria"):text.index("## 47A.")]
    numbers = [int(line.split(".")[0]) for line in section.splitlines() if line[:1].isdigit()]
    assert numbers == list(range(1, 105))


def test_readme_and_handoff_name_the_governing_architecture():
    for doc in (PROJECT_ROOT / "README.md", DOCS / "HANDOFF.md"):
        assert "Master_Architecture_v2_2_0_FROZEN.md" in doc.read_text(encoding="utf-8")
