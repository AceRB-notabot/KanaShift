# phonoshift.py
# ROT500K Family / PhonoShift — Base Library (Python port)
# PhonoShift 1.0 - ROT500K family
# Author: Felipe Daragon
# https://github.com/syhunt/kanashift

from __future__ import annotations

import hashlib
import hmac
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


# -----------------------------
# Core helpers (match JS logic)
# -----------------------------

def is_separator(ch: str) -> bool:
    return ch in (" ", "-", "'")

def is_digit(ch: str) -> bool:
    return "0" <= ch <= "9"

def is_ascii_upper(ch: str) -> bool:
    return "A" <= ch <= "Z"

def is_ascii_lower(ch: str) -> bool:
    return "a" <= ch <= "z"

def to_lower_ascii(ch: str) -> str:
    if is_ascii_upper(ch):
        return chr(ord(ch) | 0x20)
    return ch

def to_upper_ascii(ch: str) -> str:
    if is_ascii_lower(ch):
        return chr(ord(ch) & ~0x20)
    return ch

def effective_shift(shift: int, set_size: int) -> int:
    if set_size <= 1:
        return 0
    m = shift % set_size
    if m == 0:
        m = 1 if shift >= 0 else -1
    return m

def rotate_in_set_no_zero(set_chars: str, ch: str, shift: int) -> str:
    n = len(set_chars)
    idx = set_chars.find(ch)
    if idx < 0:
        return ch
    eff = effective_shift(shift, n)
    j = (idx + eff) % n
    return set_chars[j]

def derive_keystream(password: str, salt: str, iterations: int, need_bytes: int) -> bytes:
    # JS: if needBytes < 32 -> 32
    if need_bytes < 32:
        need_bytes = 32
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        max(1, int(iterations)),
        dklen=need_bytes,
    )

def transform_name_name_like_fpe(s: str, password: str, iterations: int, salt: str, direction: int) -> str:
    VOW_LO = "aeiou"
    CON_LO = "bcdfghjklmnpqrstvwxyz"

    VOW_LO_PT = "áàâãäéèêëíìîïóòôõöúùûü"
    VOW_UP_PT = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜ"

    CON_LO_PT = "ç"
    CON_UP_PT = "Ç"

    if not s:
        return s

    ks = derive_keystream(password, salt, iterations, len(s) + 64)
    kpos = 0

    out_chars: List[str] = []
    for c in s:
        if is_separator(c):
            out_chars.append(c)
            continue

        shift = (ks[kpos] + 1) * direction
        kpos += 1
        if kpos >= len(ks):
            kpos = 0

        # Digits: strict, invertible
        if is_digit(c):
            d = ord(c) - 48
            nd = (d + (shift % 10) + 10) % 10
            out_chars.append(chr(48 + nd))
            continue

        upper = is_ascii_upper(c) or (c in VOW_UP_PT) or (c in CON_UP_PT)

        lc = c
        if is_ascii_upper(lc):
            lc = to_lower_ascii(lc)

        if lc in VOW_LO:
            ch = rotate_in_set_no_zero(VOW_LO, lc, shift)
            out_chars.append(to_upper_ascii(ch) if upper else ch)
            continue

        if lc in CON_LO:
            ch = rotate_in_set_no_zero(CON_LO, lc, shift)
            out_chars.append(to_upper_ascii(ch) if upper else ch)
            continue

        if c in VOW_LO_PT:
            out_chars.append(rotate_in_set_no_zero(VOW_LO_PT, c, shift))
            continue
        if c in VOW_UP_PT:
            out_chars.append(rotate_in_set_no_zero(VOW_UP_PT, c, shift))
            continue

        if c in CON_LO_PT:
            out_chars.append(rotate_in_set_no_zero(CON_LO_PT, c, shift))
            continue
        if c in CON_UP_PT:
            out_chars.append(rotate_in_set_no_zero(CON_UP_PT, c, shift))
            continue

        out_chars.append(c)

    return "".join(out_chars)


# -----------------------------
# Optional punctuation shifting (only ¿¡ and !?)
# -----------------------------

P_OPEN = "¿¡"
P_END = "!?"

def is_shift_punct(ch: str) -> bool:
    return (ch in P_OPEN) or (ch in P_END)

def punct_shift_apply(s: str, password: str, iterations: int, salt: str, direction: int) -> str:
    if not s:
        return s

    need = sum(1 for c in s if is_shift_punct(c))
    if need == 0:
        return s

    punct_salt = salt + "|PunctShift:v1"
    ks = derive_keystream(password, punct_salt, iterations, need + 64)

    out = list(s)
    kpos = 0
    for i, c in enumerate(out):
        if not is_shift_punct(c):
            continue

        shift = (ks[kpos] + 1) * direction
        kpos += 1
        if kpos >= len(ks):
            kpos = 0

        if c in P_OPEN:
            out[i] = rotate_in_set_no_zero(P_OPEN, c, shift)
        else:
            out[i] = rotate_in_set_no_zero(P_END, c, shift)

    return "".join(out)


# -----------------------------
# Public APIs: ROT500K (base)
# -----------------------------

def rot500k_encrypt(name: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", shift_punctuation: bool = True) -> str:
    r = transform_name_name_like_fpe(name, password, iterations, salt, +1)
    if shift_punctuation:
        r = punct_shift_apply(r, password, iterations, salt, +1)
    return r

def rot500k_decrypt(obfuscated: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", shift_punctuation: bool = True) -> str:
    s = obfuscated
    if shift_punctuation:
        s = punct_shift_apply(s, password, iterations, salt, -1)
    return transform_name_name_like_fpe(s, password, iterations, salt, -1)


# -----------------------------
# HMAC helpers
# -----------------------------

def hmac_sha256_bytes(key_str: str, msg_str: str) -> bytes:
    return hmac.new(key_str.encode("utf-8"), msg_str.encode("utf-8"), hashlib.sha256).digest()


# -----------------------------
# ROT500KT (token-verified)
# -----------------------------

def is_token_sep(ch: str) -> bool:
    return ch in (" ", "-", "'", ".", ",", "!", "?", ":", ";", "\t", "\n", "\r")

def is_all_digits_str(s: str) -> bool:
    return bool(s) and all(is_digit(c) for c in s)

def is_all_upper_ascii(s: str) -> bool:
    has_letter = False
    for c in s:
        if "a" <= c <= "z":
            return False
        if "A" <= c <= "Z":
            has_letter = True
    return has_letter

CONSET = "bcdfghjklmnpqrstvwxyz"

def token_digest(password: str, salt: str, iterations: int, token_index: int, token_plain: str) -> bytes:
    msg = f"PhonoShiftTok:v1|{salt}|{iterations}|{token_index}|{token_plain}"
    return hmac_sha256_bytes(password, msg)

def make_token_check(token_plain: str, kind: str, mac_bytes: bytes, check_chars_per_token: int) -> str:
    n = max(1, int(check_chars_per_token))
    upper_mode = (kind == "alpha") and is_all_upper_ascii(token_plain)
    out = []
    for i in range(n):
        b = mac_bytes[(i * 7) & 31]
        if kind == "digits":
            out.append(chr(48 + (b % 10)))
        else:
            ch = CONSET[b % len(CONSET)]
            out.append(ch.upper() if upper_mode else ch)
    return "".join(out)

def build_plain_token_checks(plain: str, password: str, salt: str, iterations: int, check_chars_per_token: int) -> List[str]:
    checks: List[str] = []
    tok: List[str] = []
    tok_idx = 0

    def flush():
        nonlocal tok_idx
        if not tok:
            return
        t = "".join(tok)
        kind = "digits" if is_all_digits_str(t) else "alpha"
        mac = token_digest(password, salt, iterations, tok_idx, t)
        checks.append(make_token_check(t, kind, mac, check_chars_per_token))
        tok_idx += 1
        tok.clear()

    for c in plain:
        if is_token_sep(c):
            flush()
        else:
            tok.append(c)

    flush()
    return checks

def attach_checks_to_cipher(cipher: str, checks: List[str]) -> str:
    out: List[str] = []
    tok: List[str] = []
    tok_idx = 0

    def flush():
        nonlocal tok_idx
        if not tok:
            return
        if tok_idx >= len(checks):
            raise ValueError("ROT500K_TokenTagged: token/check count mismatch.")
        out.append("".join(tok) + checks[tok_idx])
        tok_idx += 1
        tok.clear()

    for c in cipher:
        if is_token_sep(c):
            flush()
            out.append(c)
        else:
            tok.append(c)

    flush()

    if tok_idx != len(checks):
        raise ValueError("ROT500K_TokenTagged: unused checks remain.")
    return "".join(out)

def strip_checks_from_tagged(tagged: str, check_chars_per_token: int) -> Optional[Tuple[str, List[str]]]:
    n = max(1, int(check_chars_per_token))

    base: List[str] = []
    given: List[str] = []
    tok: List[str] = []

    def flush() -> bool:
        if not tok:
            return True
        t = "".join(tok)
        tok.clear()
        if len(t) <= n:
            return False
        chk = t[-n:]
        base_tok = t[:-n]
        given.append(chk)
        base.append(base_tok)
        return True

    for c in tagged:
        if is_token_sep(c):
            if not flush():
                return None
            base.append(c)
        else:
            tok.append(c)

    if not flush():
        return None

    return ("".join(base), given)

def rot500k_token_tagged(
    name: str,
    password: str,
    iterations: int = 500000,
    salt: str = "NameFPE:v1",
    check_chars_per_token: int = 1,
    shift_punctuation: bool = True,
) -> str:
    cipher = transform_name_name_like_fpe(name, password, iterations, salt, +1)
    checks = build_plain_token_checks(name, password, salt, iterations, check_chars_per_token)
    out = attach_checks_to_cipher(cipher, checks)
    if shift_punctuation:
        out = punct_shift_apply(out, password, iterations, salt, +1)
    return out

@dataclass
class VerifiedResult:
    ok: bool
    value: str

def rot500k_token_tagged_decrypt(
    tagged: str,
    password: str,
    iterations: int = 500000,
    salt: str = "NameFPE:v1",
    check_chars_per_token: int = 1,
    shift_punctuation: bool = True,
) -> VerifiedResult:
    s = tagged
    if shift_punctuation:
        s = punct_shift_apply(s, password, iterations, salt, -1)

    stripped = strip_checks_from_tagged(s, check_chars_per_token)
    if not stripped:
        return VerifiedResult(False, "")

    base_cipher, given_checks = stripped
    plain = transform_name_name_like_fpe(base_cipher, password, iterations, salt, -1)
    expected = build_plain_token_checks(plain, password, salt, iterations, check_chars_per_token)

    if len(expected) != len(given_checks):
        return VerifiedResult(False, "")
    for a, b in zip(expected, given_checks):
        if a != b:
            return VerifiedResult(False, "")

    return VerifiedResult(True, plain)


# -----------------------------
# ROT500KP (prefix-verified)
# -----------------------------

ROT500K_TAG_DOMAIN = "PhonoShiftTag:v1"
PT_LETTERS = "áàâãäéèêëíìîïóòôõöúùûüÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜçÇ"

def only_letters_ascii_or_pt(c: str) -> bool:
    return ("A" <= c <= "Z") or ("a" <= c <= "z") or (c in PT_LETTERS)

def detect_case_style(plain: str) -> str:
    has_letter = False
    any_upper = False
    any_lower = False
    for c in plain:
        if not only_letters_ascii_or_pt(c):
            continue
        has_letter = True
        if "A" <= c <= "Z":
            any_upper = True
        elif "a" <= c <= "z":
            any_lower = True
        else:
            any_upper = True
            any_lower = True

    if not has_letter:
        return "title"
    if any_upper and not any_lower:
        return "upper"
    if any_lower and not any_upper:
        return "lower"
    return "title"

def apply_case_style_to_word(w: str, style: str) -> str:
    if not w:
        return w
    if style == "upper":
        return w.upper()
    if style == "lower":
        return w.lower()
    low = w.lower()
    return low[:1].upper() + low[1:]

def apply_case_style_to_phrase(phrase: str, style: str) -> str:
    return " ".join(apply_case_style_to_word(p, style) for p in phrase.split(" "))

def make_pronounceable_word_from_bytes(mac: bytes, offset: int, syllables: int) -> str:
    CSet = "bcdfghjklmnpqrstvwxyz"
    VSet = "aeiou"
    out = []
    for i in range(syllables):
        x = mac[(offset + i) & 31]
        c_idx = x % len(CSet)
        v_idx = (x // len(CSet)) % len(VSet)
        out.append(CSet[c_idx] + VSet[v_idx])
    return "".join(out)

def pick_punct_from_bytes(mac: bytes) -> str:
    puncts = ["? ", "! "]
    return puncts[mac[0] % len(puncts)]

def build_tag_prefix_for_plaintext(plain: str, password: str, iterations: int, salt: str) -> str:
    msg = f"{ROT500K_TAG_DOMAIN}|{salt}|{iterations}|{plain}"
    mac = hmac_sha256_bytes(password, msg)

    w1 = make_pronounceable_word_from_bytes(mac, 1, 3)
    w2 = make_pronounceable_word_from_bytes(mac, 4, 3)
    phrase = f"{w1} {w2}"

    punct = pick_punct_from_bytes(mac)
    style = detect_case_style(plain)
    phrase = apply_case_style_to_phrase(phrase, style)

    return phrase + punct  # ends with space

def split_tagged_prefix(tagged: str) -> Optional[Tuple[str, str]]:
    for i in range(len(tagged) - 1):
        if tagged[i] in ("?", "!") and tagged[i + 1] == " ":
            prefix = tagged[: i + 1]   # punct, no space
            cipher = tagged[i + 2 :]   # after "<punct><space>"
            if cipher:
                return (prefix, cipher)
            return None
    return None

def rot500k_prefix_tagged(
    name: str,
    password: str,
    iterations: int = 500000,
    salt: str = "NameFPE:v1",
    shift_punctuation: bool = True,
) -> str:
    cipher = transform_name_name_like_fpe(name, password, iterations, salt, +1)
    prefix = build_tag_prefix_for_plaintext(name, password, iterations, salt)
    out = prefix + cipher
    if shift_punctuation:
        out = punct_shift_apply(out, password, iterations, salt, +1)
    return out

def rot500k_prefix_tagged_decrypt(
    tagged: str,
    password: str,
    iterations: int = 500000,
    salt: str = "NameFPE:v1",
    shift_punctuation: bool = True,
) -> VerifiedResult:
    s = tagged
    if shift_punctuation:
        s = punct_shift_apply(s, password, iterations, salt, -1)

    parsed = split_tagged_prefix(s)
    if not parsed:
        return VerifiedResult(False, "")
    prefix_given, cipher = parsed

    plain = transform_name_name_like_fpe(cipher, password, iterations, salt, -1)
    expected = build_tag_prefix_for_plaintext(plain, password, iterations, salt)
    expected_no_space = expected[:-1]

    if expected_no_space != prefix_given:
        return VerifiedResult(False, "")

    return VerifiedResult(True, plain)


# -----------------------------
# ROT500KV (verified auto-select)
# -----------------------------

def contains_structured_delimiters(s: str) -> bool:
    return any(c in "{}[]\"\\<> =:" for c in s)

def count_tokens_simple(s: str) -> int:
    count = 0
    in_tok = False
    for c in s:
        if is_token_sep(c):
            in_tok = False
        elif not in_tok:
            count += 1
            in_tok = True
    return count

def min_token_len_simple(s: str) -> int:
    min_len = math.inf
    cur = 0
    in_tok = False
    for c in s:
        if is_token_sep(c):
            if in_tok:
                min_len = min(min_len, cur)
            cur = 0
            in_tok = False
        else:
            in_tok = True
            cur += 1
    if in_tok:
        min_len = min(min_len, cur)
    return 0 if min_len is math.inf else int(min_len)

def should_use_token_tagged(plain: str, check_chars_per_token: int) -> bool:
    n = max(1, int(check_chars_per_token))
    if contains_structured_delimiters(plain):
        return False
    tok_count = count_tokens_simple(plain)
    min_len = min_token_len_simple(plain)
    return tok_count >= 2 and min_len > n and len(plain) >= 6

def looks_like_rot500k_cipher(s: str, check_chars_per_token: int) -> bool:
    N = max(1, int(check_chars_per_token))
    if not s:
        return False
    trimmed = s.strip(" \t\r\n")
    if not trimmed:
        return False

    def is_ascii_letter(ch: str) -> bool:
        return ("A" <= ch <= "Z") or ("a" <= ch <= "z")

    def is_consonant_ascii(ch: str) -> bool:
        low = to_lower_ascii(ch) if ("A" <= ch <= "Z") else ch
        return low in "bcdfghjklmnpqrstvwxyz"

    def looks_like_kp_prefix_at_start(x: str) -> bool:
        for i in range(min(len(x) - 1, 49)):
            if x[i] in ("?", "!") and x[i + 1] == " ":
                if x.rfind(" ", 0, i) < 0:
                    return False
                for p in range(i):
                    ch = x[p]
                    if not is_ascii_letter(ch) and ch not in (" ", "-", "'"):
                        return False
                return True
        return False

    def looks_like_kt_token_tagged(x: str) -> bool:
        tok: List[str] = []
        good = 0
        total = 0

        def finish():
            nonlocal good, total
            if not tok:
                return
            total += 1
            t = "".join(tok)
            tok.clear()
            if len(t) > N:
                suf = t[-N:]
                ok_digits = all("0" <= ch <= "9" for ch in suf)
                ok_cons = all(is_consonant_ascii(ch) for ch in suf)
                if ok_digits or ok_cons:
                    good += 1

        for c in x:
            if is_token_sep(c):
                finish()
            else:
                tok.append(c)
        finish()

        if total < 2:
            return False
        return (good * 100) // total >= 70

    return looks_like_kp_prefix_at_start(trimmed) or looks_like_kt_token_tagged(trimmed)

def rot500kv_safe_encrypt(name: str, password: str, iterations: int, salt: str, check_chars_per_token: int, shift_punctuation: bool) -> str:
    if should_use_token_tagged(name, check_chars_per_token):
        return rot500k_token_tagged(name, password, iterations, salt, check_chars_per_token, shift_punctuation)
    return rot500k_prefix_tagged(name, password, iterations, salt, shift_punctuation)

def rot500kv_safe_decrypt(obfuscated: str, password: str, iterations: int, salt: str, check_chars_per_token: int, shift_punctuation: bool) -> VerifiedResult:
    kt = rot500k_token_tagged_decrypt(obfuscated, password, iterations, salt, check_chars_per_token, shift_punctuation)
    if kt.ok:
        return kt
    kp = rot500k_prefix_tagged_decrypt(obfuscated, password, iterations, salt, shift_punctuation)
    if kp.ok:
        return kp
    return VerifiedResult(False, "")

def rot500kv(
    name: str,
    password: str,
    iterations: int = 500000,
    salt: str = "NameFPE:v1",
    check_chars_per_token: int = 1,
    shift_punctuation: bool = True,
) -> str:
    # 0) refuse to double-encrypt
    if looks_like_rot500k_cipher(name, check_chars_per_token):
        r = rot500kv_safe_decrypt(name, password, iterations, salt, check_chars_per_token, shift_punctuation)
        if r.ok:
            return r.value

    # 1) adaptive hardening for ENCRYPTION only
    eff = max(1, int(check_chars_per_token))
    if len(name) < 12:
        eff = max(eff, 2)
    if len(name) < 6:
        eff = max(eff, 3)

    return rot500kv_safe_encrypt(name, password, iterations, salt, eff, shift_punctuation)

def rot500kv_decrypt(
    obfuscated: str,
    password: str,
    iterations: int = 500000,
    salt: str = "NameFPE:v1",
    check_chars_per_token: int = 1,
    shift_punctuation: bool = True,
) -> VerifiedResult:
    return rot500kv_safe_decrypt(obfuscated, password, iterations, salt, check_chars_per_token, shift_punctuation)