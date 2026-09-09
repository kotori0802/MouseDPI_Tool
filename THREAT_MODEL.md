# Threat Model — Mouse DPI Tool

Living threat model for the **source-only** public tree.  
Companion to `SECURITY_CODEX.md`. Not a legal clearance document.

---

## 1. Assets

| Asset | Sensitivity | Public default |
|---|---|---|
| First-party Python source | HIGH (IP) | Yes after gates |
| Session JSON / HTML reports | HIGH if real DUT/lab | Synthetic `examples/` only |
| Golden fixtures | MEDIUM | Synthetic numerics |
| Preferences (`~/.mouse_dpi_tool`) | LOW–MEDIUM | Local only |
| Portable `dist/` + Qt | HIGH (license + paths) | **Not in Git baseline** |
| Capture integrity / Findings truth | CRITICAL (evidence integrity) | Methodology public; real Sessions private |

### Catastrophic leaks

- Secrets / signing keys  
- Client confidential product/lab data  
- Absolute machine user paths in published artifacts  
- Unknown-provenance third-party code  

---

## 2. Actors

| Actor | Role |
|---|---|
| Project owner | Authors/maintains source; controls publication decisions |
| Public reader | Reads published source |
| Contributor (fork/PR) | Untrusted until review |
| Local Tool operator | Runs UI; chooses report paths |
| Malicious local input | DUT/notes/HTML injection attempts |
| Compromised dependency | Supply-chain |
| GitHub Actions (future) | Build/test — least privilege |

---

## 3. Trust boundaries

```
Operator → PySide6 UI → AppController → Session / Findings → JSON+HTML (user path)
                ↓
         CaptureEngine → RawInputSubprocessSource → fixed Popen → raw_input_bridge → Windows Raw Input
Preferences ↔ home directory
Packaging host → dist/ (out of public baseline)
Future: GitHub → Actions → deps → optional Release
```

| Crossing | Trust assumption | Control |
|---|---|---|
| UI fields → Session/HTML | Data only | Schema + `html.escape` |
| Controller → Bridge | Fixed argv | `resolve_bridge_command()`; no `shell=True` |
| Bridge → OS | Trusted helper | Frozen sibling or `-m` module |
| Session → disk | Operator-chosen dir | Atomic write; validate schema |
| Prefs → disk | Home writable | Allowlisted theme/locale |

---

## 4. Attack surfaces (summary)

| Surface | Class |
|---|---|
| Subprocess Raw Input helper | SAFE (fixed argv) |
| HTML report injection | SAFE (escaped) |
| Session/prefs JSON | SAFE / minor harden |
| Network clients in `src/` | N/A |
| `eval`/`pickle`/`shell=True` | N/A |
| Portable Qt redistrib | Separate gate |

---

## 5. Abuse cases

1. Operator pastes `<script>` into Notes → must render as text in HTML.  
2. Malicious PR tries to widen subprocess command → blocked by SC-06/SC-11.  
3. Accidental commit of `reports/` or `dist/` → `.gitignore` + checklist.  
4. Publishing real qualification Sessions → excluded from public tree by policy.  
