"""Activity log schema, validator, reader, and archive helpers.

Framework-agnostic implementation of PRP-2230 (Agent Activity Log Protocol v1).
Click-free per FXA-2230 Decisions §"vendor-neutral protocol" — Click wrappers
live in `commands/log_cmd.py`, `commands/log_validate_cmd.py`,
`commands/log_archive_cmd.py`.

Phase 2 (af log) populates: SCHEMA_LITERAL, AGENT_WHITELIST, EVENT_ENUM,
RECORD_LINE_CAP_BYTES, FILE_SIZE_CAP_BYTES, RETENTION_DAYS_DEFAULT,
DIR_SOFT_CAP_BYTES, validate_record(), compose_record().

Phase 3 (af log-validate) populates: iter_records() — transparent
loose-jsonl + archive.zip union reader.

Phase 4 (af log-archive) populates: archive_directory() — atomic 5-step
procedure (flock + tmpfile + os.replace + unlink + cleanup) per
PRP-2230 §Archival.

This file is a Phase 0 scaffolding placeholder per CHG-2231 §Phase 0.
"""
