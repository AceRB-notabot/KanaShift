![cover-v5-optimized](./kanashift-cover.gif)

# KanaShift & PhonoShift

**Password-derived, reversible text obfuscation with a Japanese visual skin. Looks Japanese, translates to something else, decodes back to the truth.**

## Overview

KanaShift is a password-based, reversible text transformation scheme for Latin and Japanese text, designed for **human-readable obfuscation of structured strings**.  
It preserves token boundaries, spacing, punctuation roles, and character classes (e.g. digits remain digits, kana remains kana), while rendering output in a Japanese-looking form.

KanaShift and its sibling **PhonoShift (ROT500K)** operate as character-by-character, password-derived polyalphabetic transforms driven by a cryptographic keystream. The design is optimized for **short, structured text** — such as identifiers, access codes, logs, and UI strings—rather than free-form natural language.

## Design Notes

Internally, ROT500K derives its keystream using **PBKDF2-HMAC-SHA256 with 500,000 iterations**, deliberately making each password-guess attempt computationally expensive. Reversal without the correct password is therefore non-trivial, unlike classic substitution ciphers such as ROT13.

Modern versions introduce a **per-message nonce** to prevent keystream reuse when the same password is used across multiple messages. Because this nonce must be stored alongside the transformed text, the scheme is **not strict format-preserving encryption (FPE)** in the cryptographic sense: the full ciphertext is longer than the plaintext. The transformed payload itself remains class-preserving and structure-aware.

KanaShift applies the same core mechanics as PhonoShift with a different visual skin, rendering transformed text using Japanese writing systems (hiragana, katakana, and optionally kanji-like ranges). The result is text that looks Japanese while remaining fully reversible with the correct parameters.

Initial implementations are provided as:
- a standalone HTML/JavaScript reference implementation (`src/`)
- a Python port with Gradio (`src-python/`)
- a cross-platform Rust application

The browser implementation serves as the **reference design**; other implementations aim to match it behavior-for-behavior.

## Live Demos

[![ KanaShift – JP skin ](https://img.shields.io/badge/demo-live-green)](https://syhunt.github.io/KanaShift/src/kanashift.html)

[![ PhonoShift – Latin ](https://img.shields.io/badge/demo-live-green)](https://syhunt.github.io/KanaShift/src/phonoshift.html)

----

### Example Outputs with Default Settings — “Rio”

| Family  | Scheme        | Input | Output                                                                 |
|---------|---------------|-------|------------------------------------------------------------------------|
| Kana    | KAN500K2      | Rio   | まによわやるんチえひふみけちなタひケんきセえお           |
| Kana    | KAN500K2T     | Rio   | セをはむたコはちぬクスすとケちめセとウエソおえな           |
| Kana JP | KAN500K2JP    | リオ  | てらをならよむぬすきをかくるはイうきのるブダ               |
| Kana JP | KAN500K2JPT   | リオ  | んれタすとはかふつるまみおうひつかうしさクゲす               |
| Phono   | ROT500K2      | Rio   | Curcuscur dur'bel culpin; ken-leskon; pas canjol hal jon kan; kus; Vae   |
| Phono   | ROT500K2T     | Rio   | Karker kasnar hus'mir bel'cus mon-pen leshes'con gun-merfun jol mer; bon — Beuk |
| Phono   | ROT500K2P     | Rio   | Nen-ninnes — mon fel. mol'nes., lanker jer der honmes ken-dolhes kaldelmer Soyobu Rerofo? Kee |

Verified variants (KT, KJPT, KP) append additional characters to enable detection of incorrect passwords during decoding.

The output looks like Japanese text, even though its meaning is hidden.
For example, “Anna” may encode to イつてう, which Google Translate renders as “It’s good”, while only the correct password recovers the original.
Latin text becomes Japanese-looking, and Japanese text remains Japanese-looking but unreadable to native speakers.

The salt value (e.g. `NameFPE:v1`) acts as a domain and version separator rather than a per-message secret, ensuring keystreams are bound to this specific algorithm and version.

---

## Version Note — ROT500K2 / KAN500K2 (V2)

> This project uses a V2 generation format (`ROT500K2`, `KAN500K2`, and variants).  
> Earlier `ROT500K / KAN500K` formats are considered legacy.

### What’s new in V2

- **Per-message nonce**  
  Prevents keystream reuse across messages encrypted with the same password.

- **PBKDF2-derived HMAC keys (verified modes)**  
  Verification no longer uses a fast HMAC directly on the password, preventing oracle attacks that bypass PBKDF2 cost.

- **Stealth framing**  
  No fixed headers, colons, or magic strings.  
  Mode and nonce are encoded as pronounceable, human-looking text.

- **Strict decoding by default**  
  Verified modes require an exact `ROT500K2 / KAN500K2` frame; base modes allow tolerant frame detection.

> Recommendation: use `ROT500K2 / KAN500K2` for all new data.

### Acknowledgment

Thanks to **Sea-Cardiologist-954** for identifying a critical weakness in v1. KAN500K2 / ROT500K2 addresses keystream-reuse attacks present in v1 by introducing a per-message random nonce that is mixed into PBKDF2 salt derivation. As a result, chosen-plaintext or known-plaintext observations from one message do not apply to any other message encrypted with the same password.

---

## What This Is (and Is Not)

KanaShift is **not** a replacement for authenticated encryption (such as AES-GCM), and it does not aim to provide semantic security for free-form natural language.

It is designed for **reversible masking of structured text**, where preserving visual form, character classes, and token boundaries matters, and where recovery is performed using a shared password. Typical use cases include identifiers, short messages, UI strings, logs, screenshots, and other human-visible text where conventional encryption would be awkward or visually obvious.

## Performance and Tuning

KanaShift derives its keystream using PBKDF2 in order to impose a configurable computational cost on each password-guess attempt. The default iteration count (500,000) is chosen to balance interactive responsiveness with meaningful resistance to offline guessing for short strings.

The default **500,000 PBKDF2 iterations** were calibrated on a macOS Mac mini (M4 Pro),
resulting in roughly **~200 ms per encode/decode** in a browser environment.
This targets a *“slow but usable”* interactive cost, comparable in wall-clock time
to common bcrypt deployments (e.g. cost factor ~12), without claiming equivalent
security guarantees.

For longer text, bulk processing, or low-risk scenarios, the iteration count can be reduced substantially. This trades brute-force resistance for throughput while preserving full reversibility and the scheme’s structure-preserving behavior.

### Security Posture and Use Cases

KanaShift uses standard cryptographic primitives (PBKDF2-HMAC-SHA256, domain separation, and per-message nonces) to make unauthorized reversal **computationally expensive**, while intentionally preserving text structure and usability. With a strong password, large-scale guessing becomes impractical due to the enforced key-derivation cost.

It is designed for **reversible masking of structured, human-readable text** in UIs, logs, demos, identifiers, and test data—where stable tokenization, copy/paste friendliness, and visually plausible output matter more than producing opaque ciphertext.

Version 2 of KanaShift includes a **per-message nonce**, preventing keystream reuse across messages. The required header is itself **masked into kana**, so outputs remain visually uniform. As a result, KanaShift is no longer format-preserving in the strict cryptographic sense, but preserves format at the payload level.

KanaShift does not aim to replace authenticated encryption or provide semantic security for natural language. Its security model is explicit and reviewable, and as an open-source project it relies on scrutiny rather than obscurity.

---

## Shared Core

- Keyed and reversible (`password + salt + iterations`)
- Payload-level format preservation (keeps `space`, `-`, `'`)
- Class-preserving rotations (no cross-class mapping, no zero-shifts)
- PBKDF2-HMAC-SHA256–derived keystream
- Per-message nonce to prevent keystream reuse (masked header)
- Optional verification variants (decode can return **OK / FAILED**)

---

## PhonoShift (ROT500K)

![cover-v5-optimized](./phonoshift-cover.gif)

- Stays in Latin / ASCII
- Phonetic rotation
  - vowels rotate within vowels
  - consonants rotate within consonants
  - case preserved
- Digits stay digits
- Optional punctuation swapping (role-sets, position-preserving)

**Modes:**  
`ROT500K2` (base), `ROT500K2T` (token-verified), `ROT500K2P` (prefix-verified), `ROT500K2V` (auto)

---

## KanaShift (KAN500K)

![cover-v5-optimized](./kanashift-cover.gif)

- Switches to Japanese scripts for visual disguise

**Families**
- **Skin (Latin → Kana)**  
  lowercase → hiragana, uppercase → katakana, digits → fullwidth
- **JP-native (JP → JP)**  
  kana stay kana, kanji stay kanji-like; embedded ASCII also obfuscated

**Modes:**  
`KAN500K2`, `KAN500K2T`, `KAN500K2JP`, `KAN500K2JPT`

---

## Key Differences

| Aspect         | PhonoShift (ROT500K) | KanaShift (KAN500K) |
|----------------|----------------------|----------------------|
| Visual script  | Latin / ASCII        | Japanese (kana/kanji) |
| Main goal     | Subtle scrambling    | Visual disguise      |
| Case handling | Upper/lower preserved | Uppercase via katakana |
| Digits        | ASCII digits 0–9     | Fullwidth digits ０–９ |
| JP support    | No                   | Yes                  |
| Best use      | IDs, logs, UI text   | JP text, strong masking |

---

## Usage

- **Browser:** open the HTML file in `src/` or use the hosted GitHub Pages link.
- **Rust:** get it from https://github.com/DaragonTech/KanaShift-RS. Build with `cargo build -p kanashift_app --release` and run the binary from `target/release/`.
- **Python:** install Gradio (`pip install gradio`) and run `python kanashift_app.py`.

For the Rust implementation, performance measurements assume a release build, as debug builds can significantly slow down encoding and decoding.

### Quick Pick

- Stay Latin → PhonoShift / ROT500K
- Need verification → ROT500KV
- Want strong visual disguise → KanaShift
- Mixed JP + EN text → KAN500KJP

---
Authored by the cybersecurity professional and programmer Felipe Daragon, with AI assistance.
This project is experimental, not production-ready, and is shared for learning, testing, and review.
This code has not been formally audited and should not be considered cryptographically bulletproof.
Independent review by cryptography experts is encouraged.

Released under the **a 3-clause BSD license** for research and experimental use - see the LICENSE file for details.