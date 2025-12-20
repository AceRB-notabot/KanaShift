# ROT500K Family (PhonoShift): Keyed, format-preserving obfuscation with adaptive verification

## Abstract

**PhonoShift**, implemented as the **ROT500K family**, is a keyed, reversible, **format-preserving obfuscation** scheme for human-readable text. ROT500K applies **polyalphabetic, class-preserving rotations** to characters using a keystream derived from **PBKDF2-HMAC-SHA-256** (default **500,000 iterations**, hence “500K”). The result is text that remains structurally usable (same delimiters, similar readability properties) while hiding meaning in a deterministic, password-controlled way.

The family contains a base transform that keeps length unchanged (**ROT500K**) and verified variants that **embed a verification signal** so decode can return a definitive **OK/FAILED** under incorrect parameters (**ROT500KV**, **ROT500KT**, **ROT500KP**). A small offline demo UI exists as a wrapper around these modes, but the design is independent of any UI.

___

## Design goals

ROT500K targets scenarios where you want “scrambled but still text-like” output:

1.  **Reversible, keyed obfuscation**  
    Same _(password, salt, iterations)_ yields correct decoding.
    
2.  **Format preservation**  
    Separators such as **space**, **\-**, and **'** remain fixed so token boundaries are stable.
    
3.  **Class preservation**  
    Digits remain digits, letters remain letters, and case is preserved for ASCII letters.
    
4.  **Pronounceability-aware rotation (PhonoShift)**  
    ASCII letters rotate in **phonetic classes** rather than across the whole alphabet:
    
    -   vowels rotate within vowels
        
    -   consonants rotate within consonants  
        This avoids outputs that look like random noise and helps preserve a “word-like” texture.
        
5.  **Optional punctuation hiding without moving punctuation**  
    A reversible punctuation swap can reduce semantic cues (e.g., question vs exclamation) while keeping punctuation positions unchanged.
    

___

## Core primitive: PBKDF2 keystream + non-zero rotations

### Keystream derivation

For an input string `s`, ROT500K derives a byte stream:

-   `ks = PBKDF2_SHA256(password, salt, iterations, needBytes)`
    

This keystream is then consumed sequentially (wrapping if needed) to compute a **position-dependent shift** per character.

### Non-zero rotation rule

To avoid leaking unchanged characters, the transform forces shifts to never be zero:

-   `shift = (ks[i] + 1) * direction`
    
-   decrypt uses `direction = -1`
    

That “+1” guarantees every affected character changes (for any set of size > 1), while preserving perfect invertibility.

### Separator invariance

Characters used as structural separators are not transformed:

-   space `" "`
    
-   hyphen `"-"`
    
-   apostrophe `"'"`
    

This ensures that token boundaries and common formatting conventions remain intact.

___

## ROT500K base mode (no length increase)

**ROT500K** is the minimal, length-preserving transform.

### What it transforms

-   **Digits (0–9)**: rotated inside 10 digits → still digits
    
-   **ASCII letters**:
    
    -   vowels rotate within `aeiou`
        
    -   consonants rotate within `bcdfghjklmnpqrstvwxyz`
        
    -   case is preserved (uppercase stays uppercase, lowercase stays lowercase)
        
-   **Portuguese accented vowels**: rotated within dedicated sets (both lower and upper)
    
-   **Portuguese ç / Ç**: included as their own tiny sets (effectively toggled/rotated in a set of size 1–2 depending on implementation detail)
    

### What it leaves alone

-   separators (space, `-`, `'`)
    
-   any character not classified into a handled set (symbols, emojis, etc.) passes through unchanged unless punctuation shifting is enabled.
    

**Key property:** output length equals input length.

___

## Optional punctuation shifting

ROT500K includes an optional, reversible punctuation swap step that **does not move punctuation positions**.

In the shown implementation, punctuation shifting is intentionally minimal:

-   opening marks set: `¿¡`
    
-   ending marks set: `!?`
    

Each punctuation character in those sets rotates within its own small set using a keystream derived from a **punctuation-specific salt suffix** (so punctuation uses an independent sub-stream).

**Purpose:** hide the semantic hint of “question vs exclamation” while keeping sentences visually readable and preserving layout.

___

## The verification problem: why verified modes exist

A pure reversible obfuscation transform has a classic issue:

> If you decode with the wrong password/salt/iterations, you still get _some_ output.  
> It may look plausible, and there’s no built-in way to know it’s wrong.

ROT500K addresses this with verified variants that embed a **keyed authenticity signal** in the text itself, allowing decode to return **true/false**.

___

## Verified family overview

### ROT500KT — Token-verified (adds chars per token)

**Idea:** append `N` verification characters to every token.

1.  Split plaintext into tokens using token separators (space, punctuation, newlines, etc.).
    
2.  For each token `t` at index `i`, compute:
    
    -   `mac = HMAC_SHA256(password, "domain|salt|iterations|i|t")`
        
3.  Convert bytes into `N` check characters:
    
    -   digit-only tokens → check chars are digits
        
    -   other tokens → check chars are consonant letters (optionally uppercase if token is all-caps)
        
4.  Append the check characters to the corresponding token in the ciphertext.
    

On decode:

-   strip the last `N` chars from each token
    
-   decode the base cipher
    
-   recompute expected checks from the recovered plaintext
    
-   compare → **OK/FAILED**
    

**Traits**

-   “Stealthy” (no obvious header)
    
-   Robust for medium/long text with multiple tokens
    
-   Increases length by `N * tokenCount`
    

___

### ROT500KP — Prefix-verified (adds a word-like prefix)

**Idea:** prepend a short, human-looking tag derived from the plaintext, so even very short inputs can be verified.

1.  Compute a MAC over the entire plaintext:
    
    -   `mac = HMAC_SHA256(password, "domain|salt|iterations|plain")`
        
2.  Generate a **pronounceable prefix** (e.g., two short pseudo-words) from MAC bytes.
    
3.  Add a punctuation marker and a space (e.g., `"? "` or `"! "`), then the ciphertext:
    
    -   `"<prefix>? <cipher>"`
        

On decode:

-   parse prefix until `"? "` or `"! "`
    
-   decode remainder
    
-   recompute expected prefix from decoded plaintext
    
-   compare → **OK/FAILED**
    

**Traits**

-   Best for **very short** strings (single token, short IDs)
    
-   Verification overhead is constant-ish (a fixed prefix)
    
-   More visible than KT (because it’s a header)
    

___

### ROT500KV — Verified auto (adaptive)

**ROT500KV** is a convenience “best choice” wrapper:

-   For suitable inputs (multiple tokens, not too short, tokens longer than `N`), it selects **ROT500KT**
    
-   Otherwise it selects **ROT500KP**
    

Additionally, it may **increase `checkCharsPerToken` automatically for short plaintexts** (e.g., minimum 2 or 3) to reduce false-OK probability when the message is tiny.

It also includes a “don’t double-encrypt by accident” behavior:

-   If input _looks like_ ROT500K ciphertext (heuristics), it tries to decrypt first; if verification succeeds, it returns plaintext.
    

___

## Comparison to ROT13

ROT13 is:

-   fixed, unkeyed substitution
    
-   trivially recognizable
    
-   trivially reversible
    

ROT500K is:

-   **keyed**
    
-   **polyalphabetic** (position-dependent mapping)
    
-   expensive to brute-force _parameters_ due to PBKDF2 cost
    
-   optionally **verifiable** (KV/KT/KP), enabling definitive wrong-key detection
    

___

## Practical guidance

-   Use **ROT500K** when you _must_ preserve length exactly and don’t need “wrong password” detection.
    
-   Use **ROT500KV** when you want a safe default that:
    
    -   embeds verification
        
    -   adapts to short vs long text automatically
        
-   Use **ROT500KT** explicitly when you want stealthy verification on token-rich text.
    
-   Use **ROT500KP** explicitly when inputs are short (IDs, single words, short labels) and you still need verification.
    

___

## Security posture (what it is and isn’t)

ROT500K is designed as **format-preserving obfuscation**, not conventional ciphertext. It’s optimized for human-text workflows: stable separators, readable structure, deterministic reversal, and optional verification signals. For high-stakes confidentiality of arbitrary data, use standard authenticated encryption; for “scramble this text but keep it text-shaped,” ROT500K is purpose-built.