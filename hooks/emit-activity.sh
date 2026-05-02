#!/usr/bin/env bash
# Reference Claude Code Stop hook for the Alfred activity log protocol.
#
# Per PRP-2230 + CHG-2231 Phase 5: emits one task.done event per Claude
# Code turn via `af log ... || true` (fail-open at the hook boundary —
# emit failure cannot break a coding session).
#
# Per PRP-2230 §Decisions §"session_id and agent_version: agent-provided
# when available, sentinel fallback":
#   - $ALFRED_SESSION_ID is read by `af log` if exported (preserves
#     cross-tool correlation when harness exposes a stable session id);
#     otherwise UUIDv4 is generated.
#   - $ALFRED_AGENT_VERSION is read by `af log` if exported; otherwise
#     the literal sentinel "unknown" is used.
#
# This file is a Phase 0 scaffolding placeholder per CHG-2231 §Phase 0;
# the actual emit-activity invocation lands with the Phase 5
# implementation, alongside settings.json hook registration and the
# integration smoke test.

# Phase 5 will replace this with the live invocation:
# af log "${CLAUDE_TURN_DESCRIPTION:-claude-code turn complete}" \
#   --event task.done \
#   --agent claude-code \
#   --agent-version "${CLAUDE_VERSION:-unknown}" \
#   || true

exit 0
