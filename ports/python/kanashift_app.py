# kanashift_app.py
# KanaShift 1.0 — Gradio UI (compat: no Blocks(css=...))
# KanaShift - ROT500K family
# Author: Felipe Daragon
# https://github.com/syhunt/kanashift

import gradio as gr
import kanashift as ks


CSS = """
<style>
#title { margin-bottom: 0.25rem; }
.small { opacity: 0.90; font-size: 0.92rem; }
</style>
"""

ABOUT_MD = r"""
## About KanaShift

This demo contains **two families**:

- **“Japanese-looking skin” family** (Latin/PT → kana render):
  letters become **hiragana/katakana-heavy**, punctuation can be translated to **JP fullwidth**,
  separators (`space`, `-`, `'`) stay fixed. **Uppercase is preserved** by mapping ASCII uppercase into katakana sets.

- **JP-native family** (JP → JP):
  Japanese stays Japanese — **hiragana rotates within hiragana**, **katakana within katakana**, and **kanji** stays kanji-like
  (rotated inside the CJK block). **ASCII segments are also obfuscated** (A–Z / a–z / 0–9).

**Modes:**
- Base modes: no verification.
- **KT**: token verification (adds chars per token; decode returns OK/FAILED).
"""


def do_encode(mode: str, text_in: str, password: str, iterations: int, salt: str, check_chars: int, shift_punct: bool):
    try:
        iterations = max(1, int(iterations))
        check_chars = max(1, int(check_chars))
        salt = salt or "NameFPE:v1"

        if mode == "KAN500K":
            out = ks.kanashift_skin_encrypt(text_in, password, iterations, salt, shift_punct)
            return out, "Encoded (KAN500K skin). (No verification)"
        if mode == "KAN500KT":
            out = ks.kanashift_skin_token_encrypt(text_in, password, iterations, salt, check_chars, shift_punct)
            return out, "Encoded (KAN500KT skin)."

        if mode == "KAN500KJP":
            out = ks.kanashift_jp_encrypt(text_in, password, iterations, salt, shift_punct)
            return out, "Encoded (KAN500KJP). (No verification)"
        if mode == "KAN500KJPT":
            out = ks.kanashift_jp_token_encrypt(text_in, password, iterations, salt, check_chars, shift_punct)
            return out, "Encoded (KAN500KJPT)."

        return "", f"Error: Unknown mode {mode!r}"

    except Exception as e:
        return "", f"Error: {e}"


def do_decode(mode: str, text_in: str, password: str, iterations: int, salt: str, check_chars: int, shift_punct: bool):
    try:
        iterations = max(1, int(iterations))
        check_chars = max(1, int(check_chars))
        salt = salt or "NameFPE:v1"

        if mode == "KAN500K":
            out = ks.kanashift_skin_decrypt(text_in, password, iterations, salt, shift_punct)
            return out, "Decoded. (No verification in KAN500K)"
        if mode == "KAN500KT":
            r = ks.kanashift_skin_token_decrypt(text_in, password, iterations, salt, check_chars, shift_punct)
            return r.value, f"Decoded. Verified: {'OK' if r.ok else 'FAILED'}"

        if mode == "KAN500KJP":
            out = ks.kanashift_jp_decrypt(text_in, password, iterations, salt, shift_punct)
            return out, "Decoded. (No verification in KAN500KJP)"
        if mode == "KAN500KJPT":
            r = ks.kanashift_jp_token_decrypt(text_in, password, iterations, salt, check_chars, shift_punct)
            return r.value, f"Decoded. Verified: {'OK' if r.ok else 'FAILED'}"

        return "", f"Error: Unknown mode {mode!r}"

    except Exception as e:
        return "", f"Error: {e}"


def do_swap(text_in: str, text_out: str):
    return text_out, text_in, "Swapped."


def build_app():
    with gr.Blocks(title="KanaShift — Gradio Demo") as demo:
        gr.HTML(CSS)

        gr.Markdown("# KanaShift — Offline Demo (Gradio Port)", elem_id="title")
        gr.Markdown(
            "**KanaShift (a ROT500K mod)** is a keyed, format-preserving obfuscation scheme driven by a PBKDF2-derived keystream "
            "(default **500,000 iterations**).",
            elem_classes=["small"],
        )

        with gr.Tabs():
            with gr.TabItem("Demo"):
                with gr.Row():
                    mode = gr.Dropdown(
                        choices=["KAN500K", "KAN500KT", "KAN500KJP", "KAN500KJPT"],
                        value="KAN500K",
                        label="Mode",
                    )
                    check_chars = gr.Number(value=1, precision=0, minimum=1, label="Token check chars (KT)")

                shift_punct = gr.Checkbox(value=True, label="Punctuation hide (optional) — keyed shifting of JP punctuation glyphs")

                text_in = gr.Textbox(
                    label="Input (plaintext or obfuscated)",
                    lines=4,
                    value="Testing KanaShift with mixed English content. 完了。",
                )

                with gr.Row():
                    password = gr.Textbox(label="Password", value="correct horse battery staple")
                    iterations = gr.Number(label="PBKDF2 iterations", value=500000, precision=0, minimum=1)
                    salt = gr.Textbox(label="Salt", value="NameFPE:v1")

                with gr.Row():
                    btn_enc = gr.Button("Encode")
                    btn_dec = gr.Button("Decode")
                    btn_swap = gr.Button("Swap ↔")

                text_out = gr.Textbox(label="Output", lines=4)
                status = gr.Markdown("Tip: Encode writes to Output. Decode reads from Input. KT modes can verify wrong parameters.")

                btn_enc.click(
                    do_encode,
                    inputs=[mode, text_in, password, iterations, salt, check_chars, shift_punct],
                    outputs=[text_out, status],
                )
                btn_dec.click(
                    do_decode,
                    inputs=[mode, text_in, password, iterations, salt, check_chars, shift_punct],
                    outputs=[text_out, status],
                )
                btn_swap.click(
                    do_swap,
                    inputs=[text_in, text_out],
                    outputs=[text_in, text_out, status],
                )

            with gr.TabItem("About"):
                gr.Markdown(ABOUT_MD)

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch()