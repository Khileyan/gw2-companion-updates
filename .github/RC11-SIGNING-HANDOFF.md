# RC11 owner-only signing and GitHub publication handoff

**Status:** unsigned CI candidate only; no release has been published. **Never upload the Ed25519 private key.** It remains on the owner's Windows PC. The signer checks that its public half matches the exact key pinned into the Companion.

## Safeguards already in place

- Source/QA PR #8 is still draft. RC10 stays immutable.
- CI produces `rc11-local-signing-handoff-UNSIGNED` containing `GW2-Account-Companion-v5.9.0-rc.11-All-in-One-Preview.zip` and `RC11-SHA256SUMS.txt`.
- The local PowerShell script `RC11-LOCAL-PUBLISH.ps1` verifies this SHA256, requires exact RC11 filename, installed Node.js + GitHub CLI, authenticated access to `Khileyan/gw2-companion-updates`, and refusal to overwrite an existing RC11 tag.
- Default script execution is **read-only preflight**. Actual release requires `-Publish` AND an additional exact typed confirmation.
- The existing package publisher performs Ed25519 signing locally with the already-pinned public-key fingerprint, validates the signed v2 manifest and asset hash, creates a GitHub prerelease, and only **then** updates `main/preview.json` once the release is public.
- It also archives the previous signed preview manifest for rollback without overwriting existing archived versions. Any failure requires manual inspection before retrying: the GitHub release and the feed can become partially updated.

## Owner procedure (after final approval)

1. Download the latest passing `rc11-local-signing-handoff-UNSIGNED` artifact from the relevant GitHub Actions run and extract its two files into an empty local folder. Do not use the older `rc11-qa-unsigned-NOT-FOR-INSTALLATION` archive for publication.
2. Download this exact reviewed script `.github/RC11-LOCAL-PUBLISH.ps1` from the approved commit, not an untrusted copy.
3. Locate the **existing** local Ed25519 private key file that was used to sign RC10. Do not share its contents or location in a public ticket.
4. On Windows PowerShell 5.1, with Node.js and authenticated GitHub CLI available, run a **preflight without `-Publish`**:
   ```powershell
   .\RC11-LOCAL-PUBLISH.ps1 -PackageZip '.\GW2-Account-Companion-v5.9.0-rc.11-All-in-One-Preview.zip' -Checksums '.\RC11-SHA256SUMS.txt' -SigningKeyFile '<LOCAL-PRIVATE-KEY-PATH>'
   ```
5. Only after final approval, run the same command with `-Publish`. Enter `PUBLISH RC11` when asked. Publishing is an external irreversible action and changes the public update feed.
6. Verify `https://github.com/Khileyan/gw2-companion-updates/releases/tag/v5.9.0-rc.11`, the public `preview.json` signature/sha256/version, and complete the Windows live acceptance tests before declaring the upgrade successful.

## Stop conditions

Do NOT publish if the signing key is lost or its fingerprint mismatches, GitHub CLI is unauthenticated, a version-11 tag/release already exists, the selected CI SHA is not the reviewed one, tests failed, or RC11 has not passed a final release-security review. Do NOT generate a replacement signing key and silently change the Companion's public-key pin. Do NOT paste keys into chat, GitHub issues, or workflow secrets.

## Explicit limitation

The current CI package is not itself an authorized signed release. The ChatGPT GitHub connector in this environment cannot access the owner's local signing key or invoke GitHub's release-creation/asset-upload operation. Sign/publish is an owner-local step, not a server-side CI shortcut.
