# ADR-002 - This repository is an independent build of Steps 1 onward

- decision_id: ADR-002
- date: 2026-09-30
- problem: Master Architecture v2.1.1 (FROZEN) sections 40C, 49 and the
  "Current implementation position" describe a separate codebase at
  checkpoint 49d639bb as having Steps 1-12 closed, and say that foundation
  must not be rebuilt. This repository does not contain that codebase.
- options: (1) continue in the separate codebase from Step 13A;
  (2) build this repository independently from scratch.
- decision: (2) build independently. The project owner builds the other
  codebase separately; this repository does not import, copy or depend on it.
- reason: owner decision (section 46: human-owned decision).
- impact:
  - Every design rule of v2.1.1 applies to this repository unchanged.
  - Sections 40C, 49 and "Current implementation position" describe the
    other codebase only. They are not the status of this repository.
  - This repository's status register is the set of acceptance records in
    stages/*_acceptance.yaml, which use the 2A vocabulary and list what is
    NOT claimed.
  - This repository follows the 40B step order from step 2, and section 3F
    (non-blocking capabilities) once it reaches step 13.
- supersedes: none
- owner: project owner
