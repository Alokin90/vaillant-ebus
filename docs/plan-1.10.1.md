# Release 1.10.1 Plan

Status: **IMPLEMENTED — VALIDATED, REVIEWED, AND AUDITED; RELEASE GATES PENDING**
Date: 2026-09-30
Parent release: `v1.10.0`
Execution base: `c8145c6` (`main`, clean; aligned with `origin/main`)
Requested scope: open PR [#159](https://github.com/MarkBovee/vaillant-ebus/pull/159),
HMUX0 heating and DHW environmental-yield registers.

## Goal

Ship the six B516 environmental-yield sensors from PR #159 as patch release
`1.10.1`, without guessing telegram layouts or weakening the discovered-circuit,
unavailable-data, and fixture requirements.

## Risk and release decision

Risk: **release-sensitive**. This adds actively read eBUS registers and changes
user-visible sensor entities; the current PR is based on `2ff45ff` (before
`v1.10.0`), is unreviewed, and has zero reported check-runs. The local release
base is `c8145c6`.

PR #159 now includes raw ebusd request/reply frames, decoded values, full scan
identity for HMUX0 `SW0407/HW0504`, and ebusd `26.1.26.1` for all six registers.
The complete issue #161 community dump already in
`tests/fixtures/community/hmux0_issue161_2026-09-28_154109_discovery.yaml`
independently preserves the same HMUX0 scan and capture provenance, but predates
the six definitions. Treat these sources as a composite evidence fixture: retain
the existing full discovery dump unchanged, preserve all six raw telegrams and
their PR source verbatim in a companion fixture, and test decoded values against
the recorded evidence. Do not invent a full discovery export or reconstruct raw
frames from the summary table. Preserve the captured Hc monthly response date
bytes even though they differ from the request.

The absent/unsupported path remains a required regression test. The evidence
gate no longer requires another live capture or a PR-build YAML export; the
fixtures must retain source, scan, software, and ebusd provenance. The six
registers are confirmed candidates from direct forced reads on the stated
hardware. This does not establish support on other firmware or hardware.

On 2026-09-30, requested a complete YAML export from the integration's
`vaillant_ebus.export_discovery_dump` service with `grab_duration: 120`. The
reporter instead supplied the six raw frames and decoded values in
[PR comment #5913463544](https://github.com/MarkBovee/vaillant-ebus/pull/159#issuecomment-5913463544).
Independent plan-check accepted these together with the existing full #161 dump
as sufficient fixture evidence, provided the sources remain unaltered and the
absent path is tested.

## Scope

- **Must:** inspect/rebase the PR changes against current `main`; preserve all six
  requested B516 definitions and metadata. Hardware-gate the definitions to
  HMUX0 `SW0407/HW0504` using discovered scan identity.
- **Must:** preserve the complete existing #161 dump and add the six raw PR
  telegrams with their provenance as a companion community fixture. Add positive
  and absent-register regressions. Assert that runtime definitions and reads
  target the discovered physical heat-pump circuit, run only on the supported
  scan, and do not expose values when a register is absent or returns `ERR`.
  Positive tests must assert all six decoded values, including the captured
  Hc-month response bytes.
- **Must:** classify each register mapping as `confirmed`, `strong assumption`,
  or `speculative` from its fixture evidence, recording remaining uncertainty.
  Only `confirmed` or `strong assumption` mappings with explicit hardware scope
  and a safe absent path may enter the release.
- **Must:** synchronize version `1.10.1` with `tools/version.py` and add a human-
  written `CHANGELOG.md` entry.
- **Must:** pass the repository's full CI-equivalent validation, an independent
  review, an independent standard-tier audit, HA smoke testing, and a release
  gate before merge/tag/publication.
- **Could:** request the full PR-build YAML export if later review finds the
  composite evidence insufficient; reconsider only if the raw frames cannot be
  tied to the existing exact-scan fixture or cannot be decoded by the tests.
- **Could:** update or close PR #159 after its changes are incorporated into the
  release branch; do not create a duplicate feature implementation.
- **Out:** issue #161's other requests. Its B511 backup-heater counters remain
  unverified on the target layout; B516/0114 is station power, not heater-only
  power; energy-manager, live-HMU, and extra state-class requests are separate
  work or already covered by v1.10.0. Also out: protocol guesses, ebusd CSV
  changes, and unrelated cleanup.

## Stages and validation

1. **Plan-check:** independently challenge evidence, scope, circuit ownership,
   polling safety, compatibility, and proof gaps. PASS: the composite fixture
   evidence is acceptable with raw telegrams preserved verbatim and absent-path
   tests required.
2. **Execute:** create `release/1.10.1` from current `main`; integrate the
   evidence-backed PR delta and tests, then bump the synchronized version and
   changelog.
3. **Validate:** run focused B516 tests, `ruff check .`, configured format and
   mypy checks, YAML validation, `pytest -q`, version consistency, compileall,
   and `git diff --check`.
4. **Independent review and audit:** standard tier, separate contexts. Review
   correctness/regressions; audit production paths for wrong-circuit reads,
   unsafe polling, absent-register behavior, and compatibility. Continue until
   each pass has evidence-based completion or report a blocker. Any source edit
   invalidates prior evidence.
5. **HA smoke — PASS on non-target hardware:** inspected HA through HA-MCP and
   created snapshot `87737ed3` before deployment. After explicit approval,
   `scripts/deploy.sh --restart` passed 898 tests, replaced the integration,
   restarted HA, and received HTTP 200. The entry remained loaded and connected
   to ebusd `26.1.26.1`, with 188 registers and 176 entities on `hmu`, `ctlv2`,
   `vwz`, `broadcast`, and `scan`. The configuration check is valid, there are
   no active repairs or integration warnings/errors, and the entity total did
   not increase. Two `HcEnvYield` entities read unavailable and no `HwcEnvYield`
   entities were found; this covers only the absent-data path. The installed
   hardware is not HMUX0 `SW0407/HW0504`, so positive reads of the six new
   counters remain unverified on the target hardware.
6. **Release PR and gate:** commit/push the release branch and open a release PR
   to `main`; wait for required PR checks. Then run the independent release gate
   against the exact candidate diff and all prior evidence. Merge only after
   those checks and the gate pass; create annotated `v1.10.1` on the merged
   commit, push the tag, and verify the tag workflow and published zip. Reconfirm
   branches, tags, and remote state immediately before any push; never
   force-push.

## Gate ledger

| Gate | Status | Evidence |
|---|---|---|
| PLAN_CHECK | PASS | Independent check accepted the PR raw frames plus existing full #161 scan/provenance dump as composite evidence; other #161 requests remain out of scope |
| Evidence fixture | PASS | Verbatim six-frame evidence from PR #159 accompanies the unchanged complete #161 dump; tests cover all values and absent/ERR behavior |
| VALIDATE | PASS | 898 tests; Ruff lint/format, strict mypy, YAML parse, version check, compileall, and diff check passed on the candidate |
| REVIEW | PASS | Independent review passed the candidate worktree after the plan ledger correction |
| AUDIT | PASS | Independent standard-tier audit found no circuit ownership, polling, or unavailable-data issues; target-HW live reads remain unverified |
| HA smoke | PASS, non-target hardware | Snapshot `87737ed3` completed before deploy; deploy validation passed (898 tests), HA restarted with HTTP 200, entry loaded and connected, no ERROR/WARNING logs or active repairs; current non-target scan did not exercise the six positive reads |
| RELEASE_GATE | NOT STARTED | Must follow successful release-PR checks and consume all prior evidence |

## Audit budget

Use standard tier for both final independent review and audit because the code
delta is small but the release adds six active register reads with circuit and
absent-path safety requirements. Escalate if either pass finds unresolved
cross-cutting behavior. Candidate: uncommitted `release/1.10.1` worktree based
on `c8145c6`; final review and audit must consume the exact candidate diff.
