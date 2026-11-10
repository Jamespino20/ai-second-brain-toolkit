# Security Policy

## Supported Versions

Only the latest release on the `main` branch is actively supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| < 1.0   | :x:                |

---

## Security Philosophy & Threat Model

The **AI Second Brain Toolkit** enforces strict local fail-closed boundaries:
1. **Local Stdio Transport:** The MCP server communicates exclusively via local standard input/output (stdio IPC). It never listens on a public network port or initiates outbound network calls.
2. **Cryptographic SHA-256 Grant Verification:** Tools refuse execution unless an owner grant file is provided with a matching SHA-256 hash.
3. **Fail-Closed Privacy:** Real vault notes, personal conversation transcripts, and credentials must never reside in this repository. All tests must be executed with disposable synthetic fixtures.
4. **Win32 & Path Traversal Guards:** File paths are normalized and checked for directory traversal (`..`), NTFS directory junctions, Windows drive colons (`:`), and DOS reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`, `CONIN$`, `CONOUT$`, `CLOCK$`).

---

## Reporting a Vulnerability

If you discover a potential security vulnerability or privacy leak, please do **NOT** open a public GitHub issue.

Instead, please report the vulnerability privately through one of the following methods:

1. **GitHub Private Vulnerability Reporting:**  
   Use the **"Report a vulnerability"** tab on the [Security](https://github.com/Heiron8/ai-second-brain-toolkit/security) page of this repository.
2. **Direct Contact:**  
   Contact the repository maintainer directly via GitHub ([@Heiron8](https://github.com/Heiron8)).

### What to Include in Your Report
- A description of the issue and its potential impact (e.g., path traversal, memory leak, authorization bypass).
- Steps to reproduce or a minimal synthetic proof of concept (PoC).
- Any proposed remediation or patch.

We will acknowledge receipt within 48 hours and work with you to verify and release a fix before public disclosure.
