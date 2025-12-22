# phonoshift_app.py
# ROT500K Family / PhonoShift — Gradio UI (compat: no Blocks(css=...))
# PhonoShift 1.0 - ROT500K family
# Author: Felipe Daragon
# https://github.com/syhunt/kanashift

import gradio as gr
import phonoshift as ps

ABOUT_MD = r"""
## About the ROT500K Family

**ROT500K** keeps output length identical to input and preserves separators (`space`, `-`, `'`) and character classes (digits remain digits).
It is reversible with the same **password + salt + iterations**.

**ROT500KV** is the “verified” variant. It increases output to embed a keyed verification signal so decryption can return **true/false**.
It auto-selects between:
- **ROT500KT** (token verification): appends 1+ characters per token
- **ROT500KP** (prefix verification): adds a short word-like prefix (good for short inputs)

**Punctuation shifting (optional):** only rotates within `¿¡` and `!?` (does not move punctuation positions).
"""

CSS = """
<style>
#title { margin-bottom: 0.25rem; }
.small { opacity: 0.85; font-size: 0.9rem; }
</style>
"""

def do_encode(mode: str, text_in: str, password: str, iterations: int, salt: str, check_chars: int, shift_punct: bool):
    try:
        iterations = max(1, int(iterations))
        check_chars = max(1, int(check_chars))
        salt = salt or "NameFPE:v1"

        if mode == "ROT500K":
            enc = ps.rot500k_encrypt(text_in, password, iterations, salt, shift_punct)
            dec = ps.rot500k_decrypt(enc, password, iterations, salt, shift_punct)
            ok = (dec == text_in)
            return enc, f"Encoded. Self-check (ROT500K only): {'OK' if ok else 'FAILED'}"

        if mode == "ROT500KP":
            enc = ps.rot500k_prefix_tagged(text_in, password, iterations, salt, shift_punct)
            return enc, "Encoded (ROT500KP)."

        if mode == "ROT500KT":
            enc = ps.rot500k_token_tagged(text_in, password, iterations, salt, check_chars, shift_punct)
            return enc, "Encoded (ROT500KT)."

        enc = ps.rot500kv(text_in, password, iterations, salt, check_chars, shift_punct)
        return enc, "Encoded (ROT500KV)."

    except Exception as e:
        return "", f"Error: {e}"

def do_decode(mode: str, text_in: str, password: str, iterations: int, salt: str, check_chars: int, shift_punct: bool):
    try:
        iterations = max(1, int(iterations))
        check_chars = max(1, int(check_chars))
        salt = salt or "NameFPE:v1"

        if mode == "ROT500K":
            dec = ps.rot500k_decrypt(text_in, password, iterations, salt, shift_punct)
            return dec, "Decoded. (No verification in ROT500K)"

        if mode == "ROT500KP":
            r = ps.rot500k_prefix_tagged_decrypt(text_in, password, iterations, salt, shift_punct)
            return r.value, f"Decoded. Verified: {'OK' if r.ok else 'FAILED'}"

        if mode == "ROT500KT":
            r = ps.rot500k_token_tagged_decrypt(text_in, password, iterations, salt, check_chars, shift_punct)
            return r.value, f"Decoded. Verified: {'OK' if r.ok else 'FAILED'}"

        r = ps.rot500kv_decrypt(text_in, password, iterations, salt, check_chars, shift_punct)
        return r.value, f"Decoded. Verified: {'OK' if r.ok else 'FAILED'}"

    except Exception as e:
        return "", f"Error: {e}"

def do_swap(text_in: str, text_out: str):
    return text_out, text_in, "Swapped."

def build_app():
    # No css= kwarg for old Gradio
    with gr.Blocks(title="ROT500K Family / PhonoShift — Gradio Demo") as demo:
        gr.HTML(CSS)

        gr.Markdown("# ROT500K Family (aka *PhonoShift*) — Gradio Demo", elem_id="title")
        gr.Markdown(
            "**PhonoShift (ROT500K)** is a keyed, format-preserving obfuscation scheme that applies polyalphabetic, "
            "class-preserving rotations driven by a PBKDF2-HMAC keystream. Default is **500,000 PBKDF2 iterations**.",
            elem_classes=["small"],
        )

        with gr.Tabs():
            with gr.TabItem("Demo"):
                with gr.Row():
                    mode = gr.Dropdown(
                        choices=["ROT500K", "ROT500KV", "ROT500KT", "ROT500KP"],
                        value="ROT500K",
                        label="Mode",
                    )
                    check_chars = gr.Number(value=1, precision=0, label="Token check chars (ROT500KT / ROT500KV)", minimum=1)

                shift_punct = gr.Checkbox(value=True, label="Shift punctuation (optional) — only ¿¡ and !?")

                text_in = gr.Textbox(
                    label="Input (plaintext or obfuscated)",
                    lines=4,
                    value="Vamos lá, ver se isso funciona mesmo!",
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
                status = gr.Markdown("Tip: Encode writes to Output. Decode reads from Input. In verified modes, Decode can detect wrong parameters.")

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