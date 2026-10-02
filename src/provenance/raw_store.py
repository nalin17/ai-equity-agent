"""Raw artifact store (architecture Section 4 provenance, 40A item 11).

Every downloaded file is kept exactly as received, named by its SHA-256
hash, and recorded in raw_artifacts. Every trusted fact can then be traced
back to the exact bytes it came from. Stored files are never overwritten.
"""
import hashlib
from pathlib import Path

from core.config import PROJECT_ROOT, load_config
from core.database import now_utc
from provenance.availability import parse_timestamp


class ArtifactError(Exception):
    """A raw file cannot be stored or has already been stored."""


def default_raw_dir():
    return PROJECT_ROOT / load_config()["paths"]["data_dir"] / "raw"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def store_raw_artifact(conn, source_id, file_path, retrieved_at,
                       published_at=None, publication_evidence=None, raw_dir=None):
    """Keep the file byte-for-byte and record it. Returns (artifact_id, sha256)."""
    file_path = Path(file_path)
    retrieved_at = parse_timestamp(retrieved_at).isoformat()
    if published_at is not None:
        published_at = parse_timestamp(published_at).isoformat()
        if not publication_evidence or not publication_evidence.strip():
            raise ArtifactError("A publication time must cite its evidence (architecture 5B)")
    elif publication_evidence:
        raise ArtifactError("Publication evidence given without a publication time")

    data = file_path.read_bytes()
    sha = sha256_bytes(data)
    existing = conn.execute("SELECT artifact_id FROM raw_artifacts WHERE sha256 = ?", [sha]).fetchone()
    if existing:
        raise ArtifactError(f"This exact file was already ingested as artifact {existing[0]}")

    raw_dir = Path(raw_dir) if raw_dir is not None else default_raw_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / f"{sha}{file_path.suffix.lower()}"
    if target.exists():
        if sha256_bytes(target.read_bytes()) != sha:
            raise ArtifactError(f"Stored file {target} does not match its own hash")
    else:
        target.write_bytes(data)

    cursor = conn.execute(
        "INSERT INTO raw_artifacts (source_id, sha256, original_name, stored_path, byte_size,"
        " retrieved_at, published_at, publication_evidence, recorded_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [source_id, sha, file_path.name, str(target), len(data), retrieved_at,
         published_at, publication_evidence, now_utc()],
    )
    return cursor.lastrowid, sha
