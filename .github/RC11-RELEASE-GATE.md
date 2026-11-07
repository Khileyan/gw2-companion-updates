# RC11 release-readiness gate (unpublished)

This is a release checklist for the **draft** QA branch. It is not authorization to install or publish. Never rewrite signed RC10, its immutable tag, assets, hashes, or `preview.json`.

## Scope completed in the QA branch

- [x] Shared exclusive, random-token-owned `updater/update.lock` across ordinary updates, manual rollback, CLI recovery, and rollback confirmation.
- [x] Lock-ownership assertions directly before activation, finish/commit, and restore paths.
- [x] Verified Windows launcher process identity via PID + OS creation timestamp, legacy sessions fail closed.
- [x] No silent stale-lock deletion; unverified journal archival remains disabled.
- [x] Process contention, abrupt process exit, stale-lock, tamper and rollback negative regression tests.
- [x] Linux/Windows no-publish QA checks verified at run #115: [GitHub Actions](https://github.com/Khileyan/gw2-companion-updates/actions/runs/42398831071).
- [x] Non-publishing **unsigned** RC11 versioned candidate ZIP reproducible, checked against 181 archive entries, version ordering and critical package components on both Linux and Windows (CI #126).
- [x] Linux/Windows QA gate green on final code SHA ddbb98d2d281ea35d1bea5d72d8f2da89ae4e330 (CI #126: Linux 336 passed, one Windows-only skipped; Windows QA 53/53, rollback 22/22, UI 3/3).
- [x] Current production recovery/activation call sites audited and restricted to reviewed modules in CI; `fixed-confirm.mjs` verifies exclusive ownership. Future new call sites fail source audit.
- [ ] Final release-security review, including Windows reparse points, non-cooperating filesystem writers, file identity/check–use races, retained journal backups, and crash-after-commit behavior; no claim of mathematical/absolute safety.
- [ ] Final signed RC11 release signed by authorized publisher, verified manifest and immutable GitHub asset digests.
- [ ] `preview.json` switch **only after** authorized signed release, separate explicit user approval and a staged rollback plan.
- [ ] Windows live smoke testing on user machine after approval (GUI launch, connected plugin diagnostics, manual update check, clean restart, journal and lock cleanup, backup policy).

## Release blockers / known limitations

1. **Automatic archived-journal cleanup remains deliberately disabled.** It must not be marketed as an RC11 capability.
2. A cooperative file lock prevents simultaneous cooperating Companion mutations but cannot make arbitrary local filesystem writers or Windows path redirection impossible.
3. A missing/legacy/ambiguous launcher session blocks automatic recovery and preserves evidence rather than risking data loss. Manual support may be needed.
4. Green CI is not sufficient authorization to install, merge, tag, sign or publish.

## Rollback / user safety

Never simulate intentional update failure in a user's real installation. Test crashes only in temporary CI fixtures. Never delete a preserved rollback backup or a transaction journal just to clear a blocking state. Do not log or commit private GW2 API keys, tokenized URLs, connected-account data or local user paths. Keep published RC10 unchanged until the next immutable version has explicit release approval.
