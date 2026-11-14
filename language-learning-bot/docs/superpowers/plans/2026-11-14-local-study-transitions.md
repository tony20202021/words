# Immediate local study transitions

**Goal:** Apply cached study actions immediately; synchronize results without replacing the displayed card.

**Architecture:** StudyActivity uses its existing OfflineEngine whenever the current word is cached. The displayed question supplies pick-option semantics. The local engine owns navigation through the cached batch even when connectivity returns. A serialized outbox flush acknowledges durable events; it never navigates. Retain local ratings for counters after acknowledgment.

**Tech stack:** Kotlin, Android, Robolectric, MockWebServer, coroutines.

**Spec:** User-approved analysis in this conversation: instant question/answer/next-word transitions when cached, background synchronization, stable cards, no lost/duplicate answers; retain network fallback when cache cannot serve the action.

## Constraints and decisions
- Continue in the user's existing workspace; preserve previous UI edits. No worktree, branch switch, or unrelated commits.
- Do not publish a new APK until implementation and checks succeed.
- Keep existing network path when the current word is absent from cache.
- Resolve the displayed quiz, never a differently generated cached quiz.
- Serialize outbox requests and retain unacknowledged events.
- No server card may replace an in-progress local card on sync completion.

## Tasks
- [x] Add deterministic slow-server tests: current cached question resolves immediately; advance resolves immediately; successful late sync never rewinds; several actions retain their own word IDs; shown quiz differs from cached quiz; no-cache still uses server.
- [x] Observe failures before implementing.
- [x] Add local-entry path without rendering the cached question; preserve existing answer state and visible pick options. Record reveal-answer results at the action, not only on the next screen.
- [x] Keep local navigation after reconnection. Load another batch only when the local batch is exhausted and results are confirmed; otherwise show cached-batch completion with pending results retained.
- [x] Serialize background flushes; drain newly appended events in order; preserve progress after acknowledgments and corrections.
- [x] Run targeted transition/offline/outbox tests, then complete Android unit suite and server offline tests. Review diff and any failing scenarios before release.

## Review focus
- Cache missing/current word absent and cache exhaustion.
- Shown quiz options differing from the snapshot.
- Corrections arriving during an earlier request; latest rating must win.
- HTTP failures, delayed responses, lifecycle cancellation and retry.
- Progress counters staying stable when events are acknowledged.

## Progress
- RED: initial transition tests reproduced the old question remaining visible; 5 of 6 failed, missing-current-word network fallback passed.
- GREEN: first 6 transition and 7 outbox tests passed after local navigation and serialized IO flush changes.
- Extended coverage: stale button, acknowledged progress after reopening, cache exhaustion, concurrent flush/correction ordering.
- Server offline tests: 27 passed.
- Full Android suite and independent review in progress.
- Ruling: retain local ratings in SavedProgress independently of outbox ACKs — queue deletion must not erase visible/persisted counters.
- Ruling: run serialized flush on Dispatchers.IO — pending lifecycle continuations must not block the main thread or other flush callers.

- Review found and regressions confirmed: explicit Skip must replace a recorded grade; server counters/history must reconcile corrections after ACK.
- Backend now keeps a per-session acknowledged-result ledger; counts all cached words even beyond the current server batch; batch loading and normal advance skip already acknowledged words.
- Added and observed RED: four correction/gap regressions, 500-cache/100-server-batch regression, and online fallback advancement regression.
- Updated old ahead-of-cursor history expectation: ACKed results appear in actual submission order while the cursor still stops at the first unanswered word.
- Updated reading-table baseline after inspecting the sole screenshot mismatch from the earlier approved separator/whole-word changes.

- Final validation: 304 Android tests passed; 484 BLS tests passed. Independent review findings fixed with RED/GREEN regressions. Release 6.5.0 built and published. APK versionCode 60500 and signature verified; download endpoint returns identical SHA-256; BLS /version reports 6.5.0.

## Session counter correction (6.5.1)
- Reproduced four regressions: fifth-of-five became fifth-of-300; a new cache reset global position; ACK/offline reopening lost the session position; refresh reintroduced cache capacity. All four tests failed before the fix.
- Preserve authoritative session total, daily total, and a word-relative position in SavedProgress. Use cache index only to advance relative to that word. Legacy snapshots fall back to their server metadata, never cache length.
- Verify targeted and full Android tests, build signed 6.5.1, verify download/version/signature, commit and push all completed conversation changes to origin/main as requested.

- 6.5.1 validation: all 308 Android tests and all 484 BLS tests passed. Counter review found no important issues. Signed release 6.5.1 built, signature and versionCode 60501 verified. Downloaded APK matches the served artifact; BLS reports 6.5.1. Changes prepared for the requested commit and push to origin/main.
