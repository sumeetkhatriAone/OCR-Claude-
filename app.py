"""Business-card phone scanner.

Upload / capture a photo of a card -> OCR -> find Indian mobile numbers ->
return their positions so the browser can make them tappable (WhatsApp).
"""
import io
import os
import re

import pytesseract
from flask import Flask, jsonify, render_template, request
from PIL import Image, ImageOps

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # 12 MB upload cap

MESSAGE = os.environ.get(
    "WA_MESSAGE",
    "Hello, I am Atmoratech Pvt Ltd. We provide customizable software solutions",
)

# Optional +91 / 91 / 0 prefix, then 10 digits starting 6-9, any of space - . between digits.
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\s*91[\s\-.]*)?(?:0[\s\-.]*)?([6-9](?:[\s\-.]?\d){9})(?!\d)"
)


def find_numbers(text):
    """Return [(start, end, ten_digits)] for each phone number in text."""
    found = []
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) == 10:
            found.append((m.start(), m.end(), digits))
    return found


def preprocess(img):
    img = ImageOps.exif_transpose(img).convert("L")
    w, h = img.size
    longest = max(w, h)
    if longest < 1600:  # small photos OCR badly; upscale
        scale = 1600 / longest
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return ImageOps.autocontrast(img)


def ocr_numbers(img, psm):
    data = pytesseract.image_to_data(
        img, config=f"--oem 3 --psm {psm}", output_type=pytesseract.Output.DICT
    )
    W, H = img.size

    # Group word tokens by physical line.
    lines = {}
    for i, word in enumerate(data["text"]):
        if not word.strip() or float(data["conf"][i]) < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(
            (data["left"][i], data["top"][i], data["width"][i], data["height"][i], word)
        )

    results = []
    for tokens in lines.values():
        tokens.sort(key=lambda t: t[0])
        text, spans = "", []
        for (l, t, w, h, word) in tokens:
            if text:
                text += " "
            spans.append((len(text), len(text) + len(word), l, t, w, h))
            text += word

        for start, end, digits in find_numbers(text):
            hit = [s for s in spans if s[0] < end and s[1] > start]
            if not hit:
                continue
            x1 = min(s[2] for s in hit)
            y1 = min(s[3] for s in hit)
            x2 = max(s[2] + s[4] for s in hit)
            y2 = max(s[3] + s[5] for s in hit)
            pad = 4
            results.append(
                {
                    "display": f"+91 {digits[:5]} {digits[5:]}",
                    "wa": "91" + digits,
                    "x": max(x1 - pad, 0) / W,
                    "y": max(y1 - pad, 0) / H,
                    "w": (x2 - x1 + 2 * pad) / W,
                    "h": (y2 - y1 + 2 * pad) / H,
                }
            )
    return results


@app.route("/")
def index():
    return render_template("index.html", message=MESSAGE)


@app.post("/api/scan")
def scan():
    f = request.files.get("image")
    if not f:
        return jsonify(error="No image uploaded"), 400
    try:
        img = preprocess(Image.open(io.BytesIO(f.read())))
    except Exception:
        return jsonify(error="Could not read that image"), 400

    results = []
    for psm in (11, 6):  # sparse text first, then block mode as fallback
        results = ocr_numbers(img, psm)
        if results:
            break

    # De-duplicate identical numbers (keep first box)
    seen, unique = set(), []
    for r in results:
        if r["wa"] not in seen:
            seen.add(r["wa"])
            unique.append(r)
    return jsonify(numbers=unique)


@app.get("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
