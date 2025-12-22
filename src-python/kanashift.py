# kanashift.py
# KanaShift 1.0 — Base Library (Python port of HTML demo)
# KanaShift - ROT500K family
# Author: Felipe Daragon
# https://github.com/syhunt/kanashift

from __future__ import annotations

import hashlib
import hmac
import math
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


# ============================================================
# Helpers
# ============================================================

def is_separator(ch: str) -> bool:
    return ch in (" ", "-", "'")

def is_digit(ch: str) -> bool:
    return "0" <= ch <= "9"

def is_fullwidth_digit(ch: str) -> bool:
    return "０" <= ch <= "９"

def is_ascii_upper(ch: str) -> bool:
    return "A" <= ch <= "Z"

def is_ascii_lower(ch: str) -> bool:
    return "a" <= ch <= "z"

def to_lower_ascii(ch: str) -> str:
    if is_ascii_upper(ch):
        return chr(ord(ch) | 0x20)
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

def rotate_in_set_allow_zero(set_chars: str, ch: str, shift: int) -> str:
    n = len(set_chars)
    idx = set_chars.find(ch)
    if idx < 0:
        return ch
    m = shift % n
    j = (idx + m) % n
    return set_chars[j]


def pbkdf2_keystream(password: str, salt: str, iterations: int, need_bytes: int) -> bytes:
    if need_bytes < 32:
        need_bytes = 32
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        max(1, int(iterations)),
        dklen=need_bytes,
    )

def hmac_sha256_bytes(key_str: str, msg_str: str) -> bytes:
    return hmac.new(key_str.encode("utf-8"), msg_str.encode("utf-8"), hashlib.sha256).digest()


# ============================================================
# Punctuation translation (ASCII <-> JP fullwidth)
# ============================================================

_PUNCT_ENC_MAP = {
    "?": "？",
    "!": "！",
    ",": "、",
    ".": "。",
    ":": "：",
    ";": "；",
    "(": "（",
    ")": "）",
    "[": "［",
    "]": "］",
    "{": "｛",
    "}": "｝",
    '"': "＂",
}
_PUNCT_DEC_MAP = {v: k for k, v in _PUNCT_ENC_MAP.items()}

def punct_translate(s: str, direction: int) -> str:
    if not s:
        return s
    mp = _PUNCT_ENC_MAP if direction > 0 else _PUNCT_DEC_MAP
    return "".join(mp.get(c, c) for c in s)


# ============================================================
# Keyed JP punctuation shifting (glyph sets)
# ============================================================

P_END = "！？"
P_MID = "、。・"

def _is_shift_punct(ch: str) -> bool:
    return (ch in P_END) or (ch in P_MID)

def punct_shift_apply(s: str, password: str, iterations: int, salt: str, direction: int) -> str:
    if not s:
        return s

    need = sum(1 for c in s if _is_shift_punct(c))
    if need == 0:
        return s

    ks = pbkdf2_keystream(password, salt + "|PunctShiftJP:v2", iterations, need + 64)
    kpos = 0

    out = list(s)
    for i, c in enumerate(out):
        if not _is_shift_punct(c):
            continue
        shift = (ks[kpos] & 0xFF) * direction  # allow 0; rotate_in_set_no_zero prevents 0-rotation
        kpos += 1
        if kpos >= len(ks):
            kpos = 0

        if c in P_END:
            out[i] = rotate_in_set_no_zero(P_END, c, shift)
        else:
            out[i] = rotate_in_set_no_zero(P_MID, c, shift)

    return "".join(out)


# ============================================================
# FAMILY A: “Japanese-looking skin” (Latin/PT -> kana render)
# Case-preserving: lowercase -> hiragana, uppercase -> katakana
# ============================================================

def _skin_transform(text: str, password: str, iterations: int, salt: str, direction: int) -> str:
    # Plain (ASCII)
    P_VOW_LO = "aeiou"
    P_VOW_UP = "AEIOU"
    P_CON_LO = "bcdfghjklmnpqrstvwxyz"
    P_CON_UP = "BCDFGHJKLMNPQRSTVWXYZ"

    # Portuguese vowels (accented)
    P_VOW_LO_PT = "áàâãäéèêëíìîïóòôõöúùûü"
    P_VOW_UP_PT = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜ"

    # Cedilla uses “marker” kana in your HTML
    C_CED_LO = "ゞ"  # for 'ç'
    C_CED_UP = "ヾ"  # for 'Ç'

    # Cipher sets (lowercase -> hiragana)
    C_VOW_LO = "あいうえお"  # 5
    C_CON_LO = "さしすせそたちつてとなにぬねのはひふへほま"  # 21

    # Cipher sets (uppercase -> katakana)
    C_VOW_UP = "アイウエオ"  # 5
    C_CON_UP = "サシスセソタチツテトナニヌネノハヒフヘホマ"  # 21

    # Accented vowels (24)
    C_ACC_LO = "かきくけこみむめもやゆよらりるれろわをんゐゑゔゝ"
    C_ACC_UP = "カキクケコミムメモヤユヨラリルレロワヲンヰヱヴヽ"

    if not text:
        return text

    ks = pbkdf2_keystream(password, salt, iterations, len(text) + 64)
    kpos = 0

    def map_rotate(plain_set: str, cipher_set: str, ch: str, shift: int, dirn: int) -> Optional[str]:
        n = len(plain_set)
        if n <= 1:
            return None
        idx = (plain_set.find(ch) if dirn > 0 else cipher_set.find(ch))
        if idx < 0:
            return None
        j = (idx + (shift % n)) % n
        return (cipher_set[j] if dirn > 0 else plain_set[j])

    out: List[str] = []
    for c in text:
        if is_separator(c):
            out.append(c)
            continue

        # +1 ensures never 0 shift, invertible by negating direction
        shift = ((ks[kpos] & 0xFF) + 1) * direction
        kpos += 1
        if kpos >= len(ks):
            kpos = 0

        # Digits: enc => fullwidth, dec => ASCII
        if direction > 0:
            if is_digit(c):
                d = ord(c) - 48
                nd = (d + (shift % 10) + 10) % 10
                out.append(chr(ord("０") + nd))
                continue
        else:
            if is_digit(c) or is_fullwidth_digit(c):
                d = (ord(c) - 48) if is_digit(c) else (ord(c) - ord("０"))
                nd = (d + (shift % 10) + 10) % 10
                out.append(chr(48 + nd))
                continue

        if direction > 0:
            # ASCII lowercase -> hiragana
            if c in P_VOW_LO:
                out.append(map_rotate(P_VOW_LO, C_VOW_LO, c, shift, +1) or c); continue
            if c in P_CON_LO:
                out.append(map_rotate(P_CON_LO, C_CON_LO, c, shift, +1) or c); continue

            # ASCII uppercase -> katakana
            if c in P_VOW_UP:
                out.append(map_rotate(P_VOW_UP, C_VOW_UP, c, shift, +1) or c); continue
            if c in P_CON_UP:
                out.append(map_rotate(P_CON_UP, C_CON_UP, c, shift, +1) or c); continue

            # Accented vowels
            if c in P_VOW_LO_PT:
                out.append(map_rotate(P_VOW_LO_PT, C_ACC_LO, c, shift, +1) or c); continue
            if c in P_VOW_UP_PT:
                out.append(map_rotate(P_VOW_UP_PT, C_ACC_UP, c, shift, +1) or c); continue

            # Cedilla
            if c == "ç":
                out.append(C_CED_LO); continue
            if c == "Ç":
                out.append(C_CED_UP); continue

            out.append(c)
        else:
            # Hiragana -> ASCII lowercase
            if c in C_VOW_LO:
                out.append(map_rotate(P_VOW_LO, C_VOW_LO, c, shift, -1) or c); continue
            if c in C_CON_LO:
                out.append(map_rotate(P_CON_LO, C_CON_LO, c, shift, -1) or c); continue

            # Katakana -> ASCII uppercase
            if c in C_VOW_UP:
                out.append(map_rotate(P_VOW_UP, C_VOW_UP, c, shift, -1) or c); continue
            if c in C_CON_UP:
                out.append(map_rotate(P_CON_UP, C_CON_UP, c, shift, -1) or c); continue

            # Accented vowels
            if c in C_ACC_LO:
                out.append(map_rotate(P_VOW_LO_PT, C_ACC_LO, c, shift, -1) or c); continue
            if c in C_ACC_UP:
                out.append(map_rotate(P_VOW_UP_PT, C_ACC_UP, c, shift, -1) or c); continue

            # Cedilla markers
            if c == C_CED_LO:
                out.append("ç"); continue
            if c == C_CED_UP:
                out.append("Ç"); continue

            out.append(c)

    return "".join(out)


def kanashift_skin_encrypt(text: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", shift_punctuation: bool = True) -> str:
    r = _skin_transform(text, password, iterations, salt, +1)
    r = punct_translate(r, +1)
    if shift_punctuation:
        r = punct_shift_apply(r, password, iterations, salt, +1)
    return r

def kanashift_skin_decrypt(obfuscated: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", shift_punctuation: bool = True) -> str:
    s = obfuscated
    if shift_punctuation:
        s = punct_shift_apply(s, password, iterations, salt, -1)
    s = punct_translate(s, -1)
    return _skin_transform(s, password, iterations, salt, -1)


# ============================================================
# FAMILY B: JP-native (JP -> JP) + ASCII shifting
# ============================================================

def is_kanji(ch: str) -> bool:
    cp = ord(ch)
    return 0x4E00 <= cp <= 0x9FFF

def rotate_codepoint_range_no_zero(ch: str, shift: int, lo: int, hi: int) -> str:
    cp = ord(ch)
    if cp < lo or cp > hi:
        return ch
    n = (hi - lo + 1)
    eff = effective_shift(shift, n)
    idx = cp - lo
    j = (idx + eff) % n
    return chr(lo + j)

def build_kana_set(from_cp: int, to_cp: int) -> str:
    # Keep small kana included (like your HTML)
    return "".join(chr(cp) for cp in range(from_cp, to_cp + 1))

JP_HIRA = build_kana_set(0x3041, 0x3096)
JP_KATA = build_kana_set(0x30A1, 0x30FA)

def is_hiragana(ch: str) -> bool:
    cp = ord(ch)
    return 0x3041 <= cp <= 0x3096

def is_katakana(ch: str) -> bool:
    cp = ord(ch)
    return 0x30A1 <= cp <= 0x30FA

def is_stable_jp_mark(ch: str) -> bool:
    return ch in ("ー", "々", "ゝ", "ゞ", "ヽ", "ヾ")


def rotate_ascii_alpha_phono(ch: str, shift: int) -> str:
    V = "aeiou"
    C = "bcdfghjklmnpqrstvwxyz"

    if is_ascii_upper(ch):
        low = to_lower_ascii(ch)
        if low in V:
            return rotate_in_set_allow_zero(V, low, shift).upper()
        if low in C:
            return rotate_in_set_allow_zero(C, low, shift).upper()
        return ch

    if is_ascii_lower(ch):
        if ch in V:
            return rotate_in_set_allow_zero(V, ch, shift)
        if ch in C:
            return rotate_in_set_allow_zero(C, ch, shift)
        return ch

    return ch


def _jp_native_transform(text: str, password: str, iterations: int, salt: str, direction: int) -> str:
    if not text:
        return text

    # Matches your HTML: salt + "|JPNative:v2|AsciiShift"
    ks = pbkdf2_keystream(password, salt + "|JPNative:v2|AsciiShift", iterations, len(text) + 64)
    kpos = 0

    out: List[str] = []
    for c in text:
        if is_separator(c):
            out.append(c); continue
        if is_stable_jp_mark(c):
            out.append(c); continue

        shift = (ks[kpos] & 0xFF) * direction
        kpos += 1
        if kpos >= len(ks):
            kpos = 0

        # ASCII letters: PhonoShift-style
        if is_ascii_upper(c) or is_ascii_lower(c):
            out.append(rotate_ascii_alpha_phono(c, shift))
            continue

        # Digits: enc -> fullwidth; dec -> ASCII
        if direction > 0:
            if is_digit(c):
                d = ord(c) - 48
                eff = effective_shift(shift, 10)
                nd = (d + eff + 10) % 10
                out.append(chr(ord("０") + nd))
                continue
            if is_fullwidth_digit(c):
                d = ord(c) - ord("０")
                eff = effective_shift(shift, 10)
                nd = (d + eff + 10) % 10
                out.append(chr(ord("０") + nd))
                continue
        else:
            if is_digit(c) or is_fullwidth_digit(c):
                d = (ord(c) - 48) if is_digit(c) else (ord(c) - ord("０"))
                eff = effective_shift(shift, 10)
                nd = (d + eff + 10) % 10
                out.append(chr(48 + nd))
                continue

        if is_hiragana(c):
            out.append(rotate_in_set_no_zero(JP_HIRA, c, shift)); continue
        if is_katakana(c):
            out.append(rotate_in_set_no_zero(JP_KATA, c, shift)); continue
        if is_kanji(c):
            out.append(rotate_codepoint_range_no_zero(c, shift, 0x4E00, 0x9FFF)); continue

        out.append(c)

    return "".join(out)


def kanashift_jp_encrypt(text: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", shift_punctuation: bool = True) -> str:
    r = _jp_native_transform(text, password, iterations, salt, +1)
    r = punct_translate(r, +1)
    if shift_punctuation:
        r = punct_shift_apply(r, password, iterations, salt, +1)
    return r

def kanashift_jp_decrypt(obfuscated: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", shift_punctuation: bool = True) -> str:
    s = obfuscated
    if shift_punctuation:
        s = punct_shift_apply(s, password, iterations, salt, -1)
    s = punct_translate(s, -1)
    return _jp_native_transform(s, password, iterations, salt, -1)


# ============================================================
# KT Token Verification (shared)
# ============================================================

def is_token_sep(ch: str) -> bool:
    # Matches your HTML list
    return ch in (
        " ", "　", "-", "'", ".", ",", "!", "?", ":", ";",
        "。", "、", "！", "？", "：", "；", "・",
        "「", "」", "『", "』", "（", "）", "［", "］", "｛", "｝",
        "\t", "\n", "\r"
    )

def is_all_digits_str_anywidth(s: str) -> bool:
    if not s:
        return False
    for c in s:
        if not (is_digit(c) or is_fullwidth_digit(c)):
            return False
    return True

def make_token_check(kind: str, mac: bytes, check_chars_per_token: int) -> str:
    n = max(1, int(check_chars_per_token))
    KANA_CHK = "さしすせそたちつてとなにぬねのはひふへほま"
    out = []
    for i in range(n):
        b = mac[(i * 7) & 31]
        if kind == "digits":
            out.append(chr(ord("０") + (b % 10)))
        else:
            out.append(KANA_CHK[b % len(KANA_CHK)])
    return "".join(out)

def token_digest(password: str, salt: str, iterations: int, token_index: int, token_plain: str, domain: str) -> bytes:
    msg = f"{domain}|{salt}|{iterations}|{token_index}|{token_plain}"
    return hmac_sha256_bytes(password, msg)

def build_plain_token_checks(
    plain: str,
    password: str,
    salt: str,
    iterations: int,
    check_chars_per_token: int,
    domain: str,
    norm_fn: Optional[Callable[[str], str]] = None,
) -> List[str]:
    checks: List[str] = []
    tok: List[str] = []
    tok_idx = 0

    def flush():
        nonlocal tok_idx
        if not tok:
            return
        t = "".join(tok)
        tok.clear()

        kind = "digits" if is_all_digits_str_anywidth(t) else "alpha"
        tnorm = norm_fn(t) if norm_fn else t
        mac = token_digest(password, salt, iterations, tok_idx, tnorm, domain)
        checks.append(make_token_check(kind, mac, check_chars_per_token))
        tok_idx += 1

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
            raise ValueError("TokenTagged: token/check count mismatch.")
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
        raise ValueError("TokenTagged: unused checks remain.")
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
        given.append(t[-n:])
        base.append(t[:-n])
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

@dataclass
class VerifiedResult:
    ok: bool
    value: str

# Domains from your HTML
TOK_DOMAIN_SKIN = "KanaShiftTok:v2"
TOK_DOMAIN_JP   = "KanaShiftTokJP:v2"

def _family_token_tagged_encrypt(
    plain: str,
    password: str,
    iterations: int,
    salt: str,
    check_chars_per_token: int,
    shift_punctuation: bool,
    core_transform_fn: Callable[[str, str, int, str, int], str],
    tok_domain: str,
    norm_fn: Optional[Callable[[str], str]] = None,
) -> str:
    cipher = core_transform_fn(plain, password, iterations, salt, +1)
    checks = build_plain_token_checks(plain, password, salt, iterations, check_chars_per_token, tok_domain, norm_fn)
    out = attach_checks_to_cipher(cipher, checks)

    out = punct_translate(out, +1)
    if shift_punctuation:
        out = punct_shift_apply(out, password, iterations, salt, +1)
    return out

def _family_token_tagged_decrypt(
    tagged: str,
    password: str,
    iterations: int,
    salt: str,
    check_chars_per_token: int,
    shift_punctuation: bool,
    core_transform_fn: Callable[[str, str, int, str, int], str],
    tok_domain: str,
    norm_fn: Optional[Callable[[str], str]] = None,
) -> VerifiedResult:
    s = tagged
    if shift_punctuation:
        s = punct_shift_apply(s, password, iterations, salt, -1)
    s = punct_translate(s, -1)

    stripped = strip_checks_from_tagged(s, check_chars_per_token)
    if not stripped:
        return VerifiedResult(False, "")

    base_cipher, given_checks = stripped
    plain = core_transform_fn(base_cipher, password, iterations, salt, -1)

    expected = build_plain_token_checks(plain, password, salt, iterations, check_chars_per_token, tok_domain, norm_fn)
    if len(expected) != len(given_checks):
        return VerifiedResult(False, "")
    for a, b in zip(expected, given_checks):
        if a != b:
            return VerifiedResult(False, "")

    return VerifiedResult(True, plain)


# Token normalization hooks (match your HTML: both are identity now)
def norm_token_skin(tok: str) -> str:
    return tok

def norm_token_identity(tok: str) -> str:
    return tok


# Public KT wrappers
def kanashift_skin_token_encrypt(text: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", check_chars_per_token: int = 1, shift_punctuation: bool = True) -> str:
    return _family_token_tagged_encrypt(text, password, iterations, salt, check_chars_per_token, shift_punctuation, _skin_transform, TOK_DOMAIN_SKIN, norm_token_skin)

def kanashift_skin_token_decrypt(tagged: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", check_chars_per_token: int = 1, shift_punctuation: bool = True) -> VerifiedResult:
    return _family_token_tagged_decrypt(tagged, password, iterations, salt, check_chars_per_token, shift_punctuation, _skin_transform, TOK_DOMAIN_SKIN, norm_token_skin)

def kanashift_jp_token_encrypt(text: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", check_chars_per_token: int = 1, shift_punctuation: bool = True) -> str:
    return _family_token_tagged_encrypt(text, password, iterations, salt, check_chars_per_token, shift_punctuation, _jp_native_transform, TOK_DOMAIN_JP, norm_token_identity)

def kanashift_jp_token_decrypt(tagged: str, password: str, iterations: int = 500000, salt: str = "NameFPE:v1", check_chars_per_token: int = 1, shift_punctuation: bool = True) -> VerifiedResult:
    return _family_token_tagged_decrypt(tagged, password, iterations, salt, check_chars_per_token, shift_punctuation, _jp_native_transform, TOK_DOMAIN_JP, norm_token_identity)