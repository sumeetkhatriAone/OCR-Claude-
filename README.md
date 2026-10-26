# Card Scanner → WhatsApp

Scan a business card, tap a phone number to select it, tap again to open WhatsApp
with a predefined message to that number (+91 + 10 digits).

## How it works
- Browser: take/choose a photo, it is resized and sent to the server.
- Server (Flask + Tesseract OCR): finds Indian mobile numbers and returns their positions.
- Tap a highlighted number once = select, tap again = `https://wa.me/91XXXXXXXXXX?text=...`

Recognised formats: `96247 00899`, `+91 9372033597`, `+91 93720 33597`, `093720-33597`.

## Run locally
```bash
sudo apt install tesseract-ocr        # macOS: brew install tesseract
pip install -r requirements.txt
python app.py                         # http://localhost:5000
```
Camera capture needs HTTPS on phones, so test on your phone via the deployed URL.

## Deploy (GitHub -> Render, free)
1. Push this folder to a GitHub repo.
2. On https://render.com: New -> Web Service -> connect the repo (it detects the Dockerfile).
3. Deploy. Open the `https://....onrender.com` URL on your phone.

Free instances sleep when idle, so the first scan after a pause can take ~30s.

## Change the message
Edit `MESSAGE` default in `app.py`, or set an environment variable `WA_MESSAGE` on Render.

> GitHub Pages alone will not work: it only hosts static files, and this app needs a Python server for OCR.
