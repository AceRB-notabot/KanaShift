# KanaShift (KAN500K): Keyed, format-preserving obfuscation with Japanese “skins” and optional verification

## Abstract

KanaShift is a **keyed, reversible text obfuscation scheme** designed to transform input strings into **Japanese-looking output** (or Japanese-preserving output) while keeping key structural properties intact: token boundaries, separators, and character “classes” (letters stay letter-like, digits stay digit-like, kana stays kana-like, etc.). KanaShift is _not_ encryption in the conventional “binary ciphertext” sense; it is a **format-preserving obfuscation layer** intended for cases where you want to hide meaning while keeping text visually plausible, copy/paste-friendly, and structurally stable.

A default configuration labeled **500K** uses **PBKDF2-SHA-256 with 500,000 iterations** to derive a keystream from a password+salt. The keystream drives per-character rotations inside carefully chosen alphabets, producing deterministic, reversible transformations under the same parameters.

A small offline demo UI exists only as a convenience wrapper (encode/decode fields, mode selector, and a verification indicator). The core is the transform itself.

___

## Design goals

KanaShift is built around a few practical goals:

1.  **Reversible with a password**  
    Given the same _(password, salt, iterations)_, decode returns the original text.
    
2.  **Format-preserving behavior**  
    Deliberately keeps separators such as **space**, **\-**, and **'** fixed so token boundaries remain stable (useful for logs, IDs, UI labels, filenames, etc., where delimiters matter).
    
3.  **Class preservation instead of “random bytes”**  
    Letters map to kana, digits map to digits (often fullwidth), kana stays kana (JP-native family), and punctuation can be converted to Japanese fullwidth equivalents without moving punctuation positions.
    
4.  **Uniform scrambling in mixed text**  
    In JP-native mode, embedded ASCII segments are also obfuscated so you don’t end up with obvious “plaintext islands” inside a Japanese sentence.
    

___

## Core primitive: keystream-driven rotation

At the heart of KanaShift is a simple structure:

-   Derive a keystream:  
    `keystream = PBKDF2_SHA256(password, salt, iterations)`
    
-   For each character `c` (except fixed separators), take a byte `k` and compute a **shift**.
    
-   Rotate `c` inside an appropriate **set** (alphabet) determined by its class:
    
    -   vowels rotate within vowels
        
    -   consonants within consonants
        
    -   digits within digits
        
    -   hiragana within hiragana
        
    -   katakana within katakana
        
    -   kanji within a CJK range (JP-native)
        
-   Apply the inverse (negative shift) to decode.
    

Two notable implementation choices appear in the code:

### 1) “No-zero rotation” for many sets

Some transforms enforce “never rotate by 0” (using `effectiveShift`), meaning a character typically won’t map to itself under correct operation. This avoids outputs that leak unchanged characters too often (especially in short strings), while remaining invertible because decode uses the exact opposite rotation.

### 2) Separators are intentionally stable

A small set of characters is treated as **structural separators** (space, hyphen, apostrophe). These are never rotated. This is a major part of what makes the scheme “format-preserving” in a human sense (tokenization survives).

___

## Two families (two philosophies)

### Family A — “Japanese-looking skin” (KAN500K)

This family is meant for Latin/Portuguese text and produces output that _looks_ Japanese.

**Key properties**

-   **Lowercase Latin letters → hiragana**
    
-   **Uppercase Latin letters → katakana** (case preservation via script choice)
    
-   **Digits → fullwidth digits** (０–９), still rotated
    
-   **Portuguese accented vowels** are handled via dedicated sets
    
-   **Cedilla (ç/Ç)** maps to specific kana marks (ゞ / ヾ) to preserve a distinct “this was ç” signal, still reversible
    
-   **Separators remain unchanged**: `space`, `-`, `'`
    

In short: it is a _skin_—you get kana output, but the mapping is class-aware so text remains consistent and reversible.

### Family B — JP-native (KAN500KJP)

This family is meant for text that is already Japanese (or mixed JP+EN). It tries to keep Japanese looking Japanese.

**Key properties**

-   **Hiragana rotates within the hiragana block**
    
-   **Katakana rotates within the katakana block**
    
-   **Kanji rotates within a CJK Unified Ideographs range** (0x4E00–0x9FFF) so it stays “kanji-like”
    
-   **Embedded ASCII letters are still obfuscated**, using a phonetic approach:
    
    -   vowels rotate within vowels
        
    -   consonants within consonants
        
    -   case preserved
        
-   **Digits rotate and normalize**, commonly into fullwidth on encode
    

The goal is: if you start with Japanese, you don’t end with obvious Latin artifacts or script changes—everything stays in its native visual domain.

___

## Punctuation handling (two layers)

KanaShift treats punctuation as a separate, optional concern:

### 1) Punctuation translation (ASCII ⇄ JP fullwidth)

A reversible mapping converts punctuation glyphs, without changing punctuation positions:

-   `? ! , . : ; ( ) [ ] { } "`  
    become their Japanese fullwidth or Japanese-style equivalents:
    
-   `？ ！ 、 。 ： ； （ ） ［ ］ ｛ ｝ ＂`
    

This is cosmetic but useful: it helps keep the output consistently “JP-looking.”

Importantly, the transform **does not translate** `-` or `'` because those are treated as separators with structural meaning.

### 2) Optional keyed shifting of JP punctuation glyphs

KanaShift can also _rotate_ among small sets of Japanese punctuation:

-   end marks: `！？`
    
-   mid marks: `、。・`
    

This step is:

-   keyed (derived from PBKDF2 as well, with a punct-specific salt suffix)
    
-   reversible
    
-   position-preserving
    

So punctuation stays punctuation, stays in place, but becomes less predictable.

___

## KT: Token verification (KAN500KT / KAN500KJPT)

Base modes are deterministic and reversible, but **they do not inherently tell you whether the password/salt/iterations were correct**. If you decode with a wrong password, you’ll still get _something_—just not the original.

The **KT** variant adds a verification signal by appending **check characters per token**:

1.  Split plaintext into tokens using a broad set of token separators (spaces, punctuation, JP punctuation, brackets, newlines, etc.).
    
2.  For each token, compute an **HMAC-SHA-256** digest keyed by the password over:
    
    -   domain label (separates “skin” vs “JP-native” families)
        
    -   salt
        
    -   iterations
        
    -   token index
        
    -   token content (optionally normalized)
        
3.  Convert digest bytes into **1+ check characters**:
    
    -   digits tokens get fullwidth digit checks
        
    -   other tokens get kana checks from a fixed kana set
        
4.  Append the check characters to each cipher token.
    

On decode:

-   Strip the last N check chars from each token
    
-   Decode the underlying text
    
-   Recompute expected checks from the decoded plaintext
    
-   Compare checks
    
-   Return **Verified: OK/FAILED**
    

This gives KanaShift something it otherwise lacks: a **definitive wrong-key detection mechanism**, tunable via `checkCharsPerToken` (more chars → lower false-OK probability).

___

## Security posture (what it is, and what it is not)

KanaShift is best understood as **keyed obfuscation / format-preserving scrambling** with optional integrity-like verification (KT). It is intentionally human-text-shaped and predictable in structure.

That implies:

-   It is **not** a drop-in replacement for authenticated encryption (AEAD) for high-stakes secrecy.
    
-   It **is** useful when you need:
    
    -   reversible masking of strings in UIs/logs/demos
        
    -   stable tokenization and copy/paste friendliness
        
    -   output that looks like plausible Japanese text rather than base64/hex
        
    -   optional “wrong password” detection (KT)
        

The PBKDF2 500K setting is there to make **key guessing more expensive**, not to convert the design into conventional ciphertext.

___

## Practical mode summary

-   **KAN500K**: Latin/PT → kana “skin”; no verification signal.
    
-   **KAN500KT**: same skin + per-token appended check chars; decode reports OK/FAILED.
    
-   **KAN500KJP**: JP-native rotation (kana/kanji preserved) + ASCII obfuscation; no verification.
    
-   **KAN500KJPT**: JP-native + token verification.
    

___

## Implementation notes reflected in the demo code

A few choices in the code are intentional “engineering” decisions:

-   **Separate salt domains** (e.g., `|PunctShiftJP:v2`, `|JPNative:v2|AsciiShift`, `KanaShiftTok:v2`) prevent accidental cross-reuse of the same keystream for different sub-operations.
    
-   **Case preservation** in skin mode is achieved without storing metadata: uppercase letters are mapped into katakana sets.
    
-   **Token checks** are bound to token position (`tokenIndex`) to reduce ambiguity in repeated tokens.