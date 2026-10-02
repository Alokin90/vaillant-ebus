# Release 1.10.2 Plan

Status: **RELEASE_GATE passed for PR; remote CI and merge/release gates pending**
Date: 2026-10-02
Parent release: `v1.10.1`
Execution branch: `release/1.10.2`
Execution base: `825f187` (`main`, tag `v1.10.1`)

## Goal

Fix discovery-dump raw capture for current ebusd versions, where a global grab
is already active at daemon startup. Capture only the requested interval by
diffing ebusd's before/after deduplicated counts; preserve the daemon's global
grab state. Make a successful discovery-dump service call part of the required
live Home Assistant release smoke test. Treat issue #161's disconnect/recovery
report as a separate investigation; only include a recovery code fix if local
code/log evidence establishes a defect. Ship the result as `v1.10.2` only after
the local HA instance confirms that the service writes a readable dump.

## Current evidence

- Issue [#152](https://github.com/MarkBovee/vaillant-ebus/issues/152) reports
  that the export service produced no file on v1.10.1. Its other report about
  implausible/stale F34 energy entities still lacks the exact current entity
  IDs, states, units, enablement, and source circuits requested earlier.
- Issue [#161](https://github.com/MarkBovee/vaillant-ebus/issues/161) reports
  HTTP 500 from `vaillant_ebus.export_discovery_dump` while the integration was
  stuck after an ebusd segfault. The attached log sequence says transport
  recovery began, post-definition discovery received `not_connected`, and no
  usable graph was applied. Restarting ebusd and reloading HA eventually
  restored the integration. The reporter's existing dump and logs are the
  evidence; do not ask for them again.
- On the owner's HA instance, the `vaillant_ebus` entry is loaded and the
  coordinator is polling 188 registers. A read-only log inspection shows
  ordinary polling and no recent `vaillant_ebus` recovery errors or
  `Invalid repairs platform` message. A live call to
  `vaillant_ebus.export_discovery_dump` with `grab_duration: 0` succeeded on
  2026-10-02 and logged a file at
  `/config/vaillant_ebus/discovery_dump_2026-10-02_074243.yaml`.
- The owner's HA logs contain a failure at 2026-10-02 07:10:10 through
  `dump_service.py`: `async_grab()` rejected ebusd's `grab continued` response
  as a missing `grab started` acknowledgement. The full trace shows
  `_validate_grab_response()` → `async_grab()` → `_async_export_discovery_dump_impl()`.
  This means a raw capture was already active; it is distinct from issue #161's
  disconnected/unready-coordinator report. The exporter currently fails the
  entire dump in this case, even though it already collected the register
  snapshot. The successful 07:42 export used `grab_duration: 0`.
- Closed issue [#160](https://github.com/MarkBovee/vaillant-ebus/issues/160)
  independently reports ebusd 26.1.26.1 returning `grab continued` even after
  a fresh daemon restart and attaches a v1.10.1 dump. The reporter cites the
  official [TCP client command documentation](https://github.com/john30/ebusd/wiki/3.1.-TCP-client-commands#grab):
  ebusd starts grabbing all messages automatically from v2.1.0. Source at
  `john30/ebusd` commit `38db2d28bd5622cadb6078c1662c6f7da5cef891` confirms
  `MainLoop::executeGrab()` returns `grab continued` when already active,
  `BusHandler` starts with grabbing enabled, and `BusHandler::enableGrab(false)`
  clears the shared `m_grabbedMessages` buffer. Stopping a continued session
  would erase global diagnostic data and disable future captures.
- Upstream `GrabbedMessage::setLastData()` increments a per-message count and
  retains only the last payload for that key. `grab result all` exposes those
  counts and latest payloads. The service can isolate messages observed during
  its interval by comparing two result snapshots, without stopping the daemon's
  auto-grab; this remains deduplicated and does not preserve every state
  transition for one key.
- The first v1.10.2 candidate was deployed with `scripts/deploy.sh --restart`
  on 2026-10-02. It passed 901 tests and the zero-grab HA smoke test wrote and
  parsed a valid dump with the required sections. This evidence is stale for
  the revised raw-grab algorithm below; repeat deployment and both zero-grab
  and short raw-grab smoke tests before release.
- A later count-delta candidate was also deployed and restarted successfully.
  Its one-second capture still fell back because the live `grab result all`
  includes identical visible rows with different counts (for example,
  `ctlv2 Currenterror`). The current change coalesces those counts rather than
  rejecting the interval; this earlier smoke is stale for the final diff.
- The previous candidate passed the CI-equivalent checks with 919 tests and was
  deployed with `scripts/deploy.sh --restart`; HA returned HTTP 200 and HA-MCP
  confirmed the entry loaded. Zero- and one-second service calls both succeeded.
  The zero dump
  `/config/vaillant_ebus/discovery_dump_2026-10-02_095855.yaml` parsed with the
  expected sections and `grab_status: not_requested`. The positive dump
  `/config/vaillant_ebus/discovery_dump_2026-10-02_095924.yaml` reported
  `grab_status: continued`, `grab_capture_method: count_delta`, measured
  duration `1.00069` s, and the capture limitation; its `grab` section contains
  the continued marker and one interval telegram. Both files had 631 raw find
  lines and 727 before-registers. A subsequent read-only `grab result all`
  returned 8,213 lines rather than `grab disabled`. Fresh HA-MCP system logs had
  no `vaillant_ebus` warnings/errors. This evidence predates the latest fallback
  and duration changes and must be repeated.
- The previous 928-test candidate was deployed through `scripts/deploy.sh --restart`
  and HA-MCP confirmed the integration loaded. The zero-second dump at
  `/config/vaillant_ebus/discovery_dump_2026-10-02_103122.yaml` parsed with all
  required sections and `grab_status: not_requested`. The one-second dump at
  `/config/vaillant_ebus/discovery_dump_2026-10-02_103139.yaml` parsed with
  `grab_status: continued`, `grab_capture_method: count_delta`, measured
  duration `1.00141` s, and `grab_capture_limitation`; it contains one interval
  telegram beyond the continued marker. Both dumps have 631 raw find lines and
  727 before-registers. A read-only post-check returned 8,213 `grab result all`
  rows, not `grab disabled`. Fresh HA-MCP system logs had no `vaillant_ebus`
  warnings/errors.
- After the owned-ACK timing fix, the 928-test candidate was deployed again
  through the same script; HA-MCP confirmed the entry loaded and both service
  calls succeeded. `/config/vaillant_ebus/discovery_dump_2026-10-02_103808.yaml`
  parsed with `grab_status: not_requested`; the positive dump at
  `/config/vaillant_ebus/discovery_dump_2026-10-02_103824.yaml` parsed with
  `grab_status: continued`, `grab_capture_method: count_delta`, measured
  duration `1.00181` s, and the capture limitation. It contains two interval
  telegram lines plus the continued marker. Both dumps had 631 raw find lines
  and 727 before-registers. The read-only post-check again returned 8,213 lines,
  and fresh HA-MCP system logs showed no `vaillant_ebus` warnings/errors. This
  smoke predates the latest stream-line and cross-instance documentation fixes.
- The final 931-test candidate was deployed after adding over-limit TCP-line
  handling. `/config/vaillant_ebus/discovery_dump_2026-10-02_105054.yaml` parsed
  with `grab_status: not_requested`; the positive dump at
  `/config/vaillant_ebus/discovery_dump_2026-10-02_105110.yaml` parsed with
  `grab_status: continued`, `grab_capture_method: count_delta`, measured
  duration `1.00191` s, and the capture limitation. It contains two interval
  rows plus the continued marker. Both dumps had 631 raw find lines and 727
  before-registers. A read-only post-check returned 8,213 rows rather than
  `grab disabled`; fresh HA-MCP logs showed no integration errors.
- Issue [#165](https://github.com/MarkBovee/vaillant-ebus/issues/165) reports
  that BASS3 calendars disappeared after the new `{prefix}_Monday0` gate.
  Its evidence shows that BASS3 exposes `{prefix}_Monday` instead, but active
  reads return `ERR: invalid position in decode`; do not recreate calendars
  that cannot read usable schedule data or mutate the owner's entity registry.

## Risk and release decision

Risk: **significant and release-sensitive**. The export service shares
ebusd's daemon-wide capture buffer with auto-grab and external clients. The
interval diff must not confuse cumulative counts with interval observations,
stop another capture, or weaken the authoritative-discovery graph gate.

Use a separate standard-tier review (5 minutes) and deep-tier audit (8 minutes).
The change reads ebusd's shared grab, stops only a session this export explicitly
started, and keeps coordinator graph readiness unchanged. ebusd has no session
ID; external grab commands, a second export from another HA instance, and daemon
restarts are operationally forbidden races during export. The in-process lock
does not coordinate separate HA instances. Keep the independent release gate
mandatory; deploy with `scripts/deploy.sh --restart` and exercise through HA-MCP.

## Scope

- **Must — interval capture on an existing global grab:** when ebusd answers
  `grab continued`, read and validate a baseline `grab result all`, wait for the
  requested duration, then read and validate the final result. Keep only keys
  whose counts increased, replace each cumulative count with the interval delta,
  and preserve the final payload and label. Group known messages by destination
  ZZ, PB/SB, and `circuit name`; group unknown messages by destination, PB/SB,
  and effective ID prefix. Unknown effective ID length is `min(NN, 4)` (or
  `min(NN, 1)` for broadcast); raw `NN` is not a separate identity field.
  When a family has exactly one row in both snapshots, pair those rows and
  require the source QQ to stay stable. When either snapshot has multiple rows
  in a family, match by exact request, response, and label signatures; every
  baseline signature must remain, while new final signatures are new rows. Any
  ambiguous change in an existing family fails closed rather than guessing
  which bytes define the message ID. Because public output does not expose
  ebusd's master-number mapping, a QQ change is always ambiguous. Identical
  visible rows are coalesced by summing counts, not treated as ambiguous
  duplicates. Final-only families are new; baseline-only families are unsafe.
  Never send `grab stop` for a continued session. A `grab started` response is
  the only proof that this export may stop a session; because ebusd exposes no
  session ID, no external `grab`, `grab stop`, or daemon restart may occur until
  export cleanup completes. A lost start acknowledgement is ambiguous: do not
  send an unowned stop, and record that ebusd may remain grabbing.
- **Must — truthful capture metadata and safe fallback:** preserve
  `metadata.grab_duration` as the requested duration; add
  `metadata.grab_status` (`not_requested`, `captured`, `continued`,
  `skipped_active`, or `unavailable`), monotonic
  `metadata.grab_captured_duration` (elapsed time from just before the baseline
  request, or the owned-session start ACK, to just before the final result
  request), and
  `metadata.grab_capture_method` (`none`, `owned_session`, or `count_delta`). A
  continued capture must also include `metadata.grab_capture_limitation`. If
  ebusd's baseline and final state cannot be diffed safely, including `grab
  disabled`, missing baseline keys, ambiguous request sets, or decreasing
  counts, save the register snapshot only, mark `skipped_active` for a continued
  grab or `unavailable` otherwise, set captured duration to zero, and record the
  reason in `metadata.grab_error`. Identical visible rows are coalesced instead;
  other ambiguous request sets fall back.
  Reject decimal counts longer than 20 digits before integer conversion, and
  translate over-limit individual TCP lines into an unusable-snapshot fallback.
  For count-delta captures, document that ebusd keeps only the latest payload per
  message key and exposes no grab epoch; identical visible rows are coalesced
  by summing counts because each received telegram updates one internal key.
  An external stop/restart followed by a sufficiently large count refill cannot
  be detected. The service assumes no external grab command or daemon restart
  from before the baseline through owned-session cleanup and must not claim
  stronger isolation.
- **Must — service documentation:** update `services.yaml` to describe auto-grab,
  the count-delta result, latest-payload limitation, and the requirement not to
  run external `grab`/`grab stop` commands or restart ebusd during capture.
  State that a lost start acknowledgement may leave ebusd grabbing because the
  service cannot safely stop a session whose ownership it cannot confirm. State
  that only one export may run per ebusd endpoint at a time, including across
  separate HA instances.
- **Must — recovery safety:** inspect issue #161's service and coordinator
  paths. Preserve dump-export gating on a connected ebusd client and
  authoritative graph. A disconnected or non-authoritative graph must fail
  clearly without creating a misleading dump or issuing map probes. Treat the
  #161 HTTP 500 as a separate recovery defect only if code/log evidence shows an
  unexpected exception or that the coordinator fails to retry discovery after
  ebusd becomes available; do not weaken graph-readiness to make a dump appear.
- **Must — regression proof:** test baseline/final delta decoding, including
  changed counts, final-only families, one-row known/unknown families with
  changed payloads, multiple stable rows in a family, effective broadcast/slave
  ID lengths, identical visible-row count summing, missing
  baseline rows, source-address ambiguity, and reset/inconsistent-result
  fallback. Include a positive test
  with a non-empty baseline, unchanged existing families, and a new final-only
  family; verify only that family is emitted with its final count. A baseline-
  only family or missing exact row from a multi-row family makes the diff unsafe.
  Reject `grab disabled` rather than treating it as an empty snapshot. Malformed,
  incomplete, oversized-line, oversized-count, and transport-failed snapshots
  must produce the register-only fallback without stopping a continued grab.
  Verify that a 20-digit count is accepted while a 21-digit count is rejected.
  Test the unobservable reset-and-refill case as an explicit limitation, not
  proof that the result is isolated. Assert cancellation of a continued capture
  sends no `grab stop`, while cancellation of an owned `grab started` capture
  still performs cleanup. Keep the unavailable-graph rejection covered and
  exercise a normal successful export through the real implementation on the
  owner's HA server. Existing coordinator tests cover setup retries after
  transport recovery; no recovery code changes are planned without a reproduced
  defect.
- **Must — live HA test instruction:** update `AGENTS.md` so every release
  integration smoke test deploys to the owner's HA server, calls
  `vaillant_ebus.export_discovery_dump` with both `grab_duration: 0` and a short
  positive duration, reads and YAML-parses each file, verifies the expected
  sections and metadata, including `grab_capture_limitation` on the continued
  capture, and checks integration logs. After the positive-duration call, issue
  the read-only ebusd `grab result all` command and fail if it returns
  `grab disabled`; do not issue a `grab` start command, a separate `grab stop`,
  or restart ebusd during the test. This is additive to startup/entity checks.
 - **Must — issue communication:** reply in English to changed/new user threads
  #152, #160, #161, and #165 that branch `release/1.10.2` is underway. Correct
  the earlier #152/#160/#161 wording with the official auto-grab behavior; do
  not promise unrelated sensor mappings or BASS3 schedule support without
  evidence.
- **Must — release metadata:** synchronize version `1.10.2` through
  `tools/version.py` and write the matching changelog entry.
- **Explicitly deferred — #165 BASS3 calendars:** the issue's BASS3 timer reads
  return `ERR: invalid position in decode`, so this release will not restore
  calendars that cannot provide schedule data. Revisit when a decodable BASS3
  timer capture or a compatible ebusd layout is available. Reply that the
  release branch is open for investigation, not that BASS3 calendar support is
  guaranteed.
- **Could — #161 coordinator recovery:** the report's post-crash HTTP 500
  occurred before an authoritative graph was restored, and this release keeps
  that export guard. Existing coordinator tests cover fresh setup retry after
  transport loss; the owner's current logs show no recovery failure. Revisit if
  a v1.10.2 run still cannot recover after ebusd becomes reachable; request only
  the fresh post-release recovery/service logs then, because the original logs
  and dump are already available.
- **Could — #152 F34 entity values:** revisit after the exporter fix if the
  reporter supplies the exact entity IDs, values, units, enablement, and source
  circuits. The existing report does not identify which value mappings are
  wrong, so changing them now would be guesswork. Trigger: those requested
  details or a fresh post-fix dump.
- **Explicitly out — #161 feature requests:** B511 backup-heater counters,
  VWZIO power/energy semantics, additional HMUX0 telemetry, and the extra zone
  entity are separate evidence/mapping work. The current candidate includes
  only a verified recovery fix if it is causally required for export; it does
  not claim these values are fixed.
- **Explicitly out — remote cleanup:** no HA entity/device registry edits and
  no ebusd addon CSV/config changes.

## Plan-check questions

1. Does the baseline/final count delta isolate only messages seen during the
   requested interval without mutating ebusd's existing global grab?
2. Are the canonical unknown key fields correct, including effective ID length
   without raw `NN`, broadcast-vs-slave ID width, count reset, and missing-key
   paths?
3. Does #161 show a separate recovery defect, or only the intended service
   rejection while the coordinator has no authoritative graph?
4. Is explicit BASS3 calendar deferral justified by the issue's
   invalid-position evidence?
5. Does the live HA smoke test validate both a zero-grab dump and a short raw
   capture without stopping the daemon's auto-grab?

## Stages and validation

1. **Plan-check:** PASS. Independent review verified `readline()` over-limit
   fallback, the explicit cross-instance endpoint exclusion, and the 20/21-digit
   counter boundary.
2. **Inbox:** replies have been posted on #152, #160, #161, and #165; the
   auto-grab correction is now posted on #152/#160/#161. State is persisted for
   every open issue and discussion scanned. Discussion #31's old count was
   corrected from 51 to 61 after confirming all ten additional nested replies
   predated its stored timestamp. Issue #160 is recorded closed. The later
   #152 question about acceptable entity identifiers was answered; HA-style
   entity IDs are sufficient to trace, with state/unit and enabled status
   requested after the user's v1.10.2 update. The inbox sidecar is current at
   #152 update `2026-10-02T09:08:05Z` with 18 comments.
3. **Execute:** add a failing regression test first, make the smallest fix that
   preserves graph ownership/readiness, update the HA test instructions, then
   add version/changelog metadata.
4. **Validate:** focused count-delta/ownership tests, then the repository's complete
   Ruff, format, pytest, version, compileall, and diff checks. Deploy through
   `scripts/deploy.sh --restart`; run the dump service with `grab_duration: 0`
   and a short positive duration on the deployed code. Verify the YAML artifacts
   and fresh HA logs. After the positive-duration call, run read-only
   `grab result all` and verify it does not return `grab disabled`; do not issue
   `grab`, because that command can mask an inactive-capture failure.
5. **Review, audit, release gate:** separate independent standard-tier review
  and deep-tier audit, then a release-gate decision against the exact final
  diff. Any edit invalidates stale evidence. Push/open release PR, wait for
  checks, merge only after the release gate, tag the merged commit, and verify
  the published artifact.

## Gate ledger

| Gate | Status | Evidence |
|---|---|---|
| PLAN_CHECK | PASS | Independent check verified over-limit `readline()` fallback, cross-instance endpoint constraint, and counter-boundary tests |
| VALIDATE | PASS | Ruff, format, strict mypy, YAML parse, 931 pytest tests, version check, compileall, and diff check passed |
| HA_SMOKE | PASS | Final executable integration/service files deployed; zero/one-second exports parsed, continued capture reported count_delta and 1.00191 s, and read-only `grab result all` returned 8,213 lines. Later repository-only edits were limited to plan bookkeeping and test comments; no deployed file changed. |
| REVIEW | PASS | Final independent standard-tier review confirmed all prior findings closed, including direct Intent/Why comments, against the final capture paths and docs |
| AUDIT | PASS | Final independent deep audit found no remaining counterexample across over-limit lines, count bounds, ownership, external concurrency, cancellation, fallback, and graph guard |
| RELEASE_GATE | PASS for PR | Independent gate confirmed exact diff, inbox closure, and prior evidence; merge/tag/release remain blocked on remote CI, merge approval, and post-merge artifact verification |

## Audit budget

Planned review: standard tier, 5 minutes. Planned audit: deep tier, 8 minutes.
Reserve up to 3 minutes each for one delta review and one delta audit if final
gate evidence changes only the plan document; total review/audit time must stay
within 19 minutes. Carry prior cost forward and record actual time/outcome during
session review. Do not claim release readiness from tests or deployment alone.
