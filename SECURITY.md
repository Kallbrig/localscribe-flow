# Security and privacy

## Privacy guarantees

- Microphone audio, raw transcripts, cleaned text, and custom vocabulary are processed locally.
- Recordings are deleted immediately after successful transcription by default.
- The project contains no analytics, advertising SDK, account system, or remote inference API.
- The first use of a missing model contacts Hugging Face to download public model weights.
  After model setup, the app can be firewalled or used offline.

Configuration and model files are stored in the current user's application-data folders. They
are not encrypted at rest; anyone with access to the Windows account may be able to read custom
vocabulary or deliberately retained recordings.

## Reporting a vulnerability

Please use GitHub's private **Security advisories → Report a vulnerability** flow. Do not open
a public issue for an unpatched vulnerability. Include affected versions, reproduction steps,
and impact. Maintainers should acknowledge a report within seven days.

## Release integrity

Release workflows publish SHA-256 checksum files and a CycloneDX SBOM. GitHub Actions pins
actions to major release lines; Dependabot proposes updates. Windows code signing is not yet
configured, so SmartScreen may warn on the initial beta release. Do not bypass a warning unless
the downloaded file's checksum matches the release checksum.

