"""Runs through the API once and prints PASS or FAIL. Start the server first."""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path

BASE = os.environ.get("BACKSTAGE_URL", "http://127.0.0.1:8000") + "/api/v1"
results = []


def check(label, ok, detail=""):
    results.append(ok)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", label, ("   -> " + str(detail)) if detail else ""))
    return ok


def call(method, path, token=None, body=None, multipart=None):
    headers = {}
    data = None
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if multipart is not None:
        data, headers["Content-Type"] = multipart
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw)
        except ValueError:
            return error.code, raw.decode(errors="replace")[:200]


def make_multipart(fields, filename, file_bytes, content_type):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value)).encode())
    parts.append(
        ('--%s\r\nContent-Disposition: form-data; name="audio"; filename="%s"\r\nContent-Type: %s\r\n\r\n'
         % (boundary, filename, content_type)).encode() + file_bytes + b"\r\n"
    )
    parts.append(("--%s--\r\n" % boundary).encode())
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


def silent_wav(seconds):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * int(8000 * seconds))
    return buffer.getvalue()


def main():
    audio_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if audio_path and not audio_path.is_file():
        sys.exit("File not found: %s" % audio_path)

    print("Backstage API check on %s\n" % BASE)

    print("Server and login")
    try:
        status, data = call("GET", "/prompts/")
    except urllib.error.URLError:
        sys.exit("Cannot reach the server. Start it first with: python manage.py runserver")
    check("server answers, and asks for a login", status == 401 and data["error"]["code"] == "unauthorized", status)

    username = "tester_" + uuid.uuid4().hex[:8]
    status, data = call("POST", "/auth/register/", body={"username": username, "password": "StrongPass123"})
    check("register", status == 201, status)
    status, data = call("POST", "/auth/login/", body={"username": username, "password": "StrongPass123"})
    token = data.get("access") if status == 200 else None
    check("login gives a token", bool(token), status)
    if not token:
        sys.exit("Cannot go on without a token.")
    status, data = call("GET", "/auth/me/", token)
    check("me", status == 200 and data["username"] == username, data)

    print("\nPrompts and settings")
    status, data = call("GET", "/prompts/", token)
    has_prompts = status == 200 and data["count"] > 0
    check("prompts exist", has_prompts, "run: python manage.py seed_demo" if not has_prompts else "%s prompts" % data["count"])
    prompt_id = data["results"][0]["id"] if has_prompts else None
    status, data = call("GET", "/settings/", token)
    check("settings", status == 200 and "wpm_target_min" in data, status)

    print("\nUpload and processing")
    if audio_path:
        file_bytes, filename = audio_path.read_bytes(), audio_path.name
        content_type = "audio/" + audio_path.suffix.lstrip(".").lower()
    else:
        file_bytes, filename, content_type = silent_wav(15), "silence.wav", "audio/wav"
    fields = {"prompt_id": prompt_id} if prompt_id else {}
    status, data = call("POST", "/recordings/", token, multipart=make_multipart(fields, filename, file_bytes, content_type))
    check("upload is accepted (202)", status == 202, data if status != 202 else "id %s" % data["id"])
    if status != 202:
        sys.exit("Cannot go on without an upload.")
    recording_id = data["id"]

    final = None
    for _ in range(90):  # up to 3 minutes, real Whisper can be slow on a CPU
        time.sleep(2)
        status, final = call("GET", "/recordings/%s/" % recording_id, token)
        if final["status"] != "processing":
            break
    ok = final["status"] == "completed"
    check("processing finishes", ok, final["status"] if ok else final.get("error", final))

    if ok:
        status, transcript = call("GET", "/recordings/%s/transcript/" % recording_id, token)
        check("transcript", status == 200 and "words" in transcript, "engine: %s" % transcript.get("engine"))
        status, analysis = call("GET", "/recordings/%s/analysis/" % recording_id, token)
        keys = {"recording_id", "status", "duration_sec", "summary", "pacing", "fillers", "pauses"}
        check("analysis has every part", status == 200 and keys <= set(analysis), status)
        if status == 200:
            summary = analysis["summary"]
            print("        words %s | %s words/min (%s) | fillers %s %s | pauses %s" % (
                summary["total_words"], summary["wpm"], analysis["pacing"]["status"],
                summary["filler_count"], dict(analysis["fillers"]["by_word"]), summary["pause_count"]))
        status, progress = call("GET", "/progress/", token)
        check("progress lists it", status == 200 and any(r["recording_id"] == recording_id for r in progress["results"]), status)
        if transcript.get("engine") == "mock":
            print("\n  NOTE: the engine is 'mock', so these numbers are NOT from your audio.")
            print("        Whisper is not installed or its model is not downloaded yet. Run: python run.py (needs internet once)")

    print("\nFiller words")
    status, data = call("POST", "/filler-words/", token, body={"word": "literally"})
    check("add my own filler word", status == 201 and data["scope"] == "personal", status)
    status, data = call("GET", "/filler-words/", token)
    check("it shows up in my list", status == 200 and "literally" in [w["word"] for w in data["results"]], status)
    status, data = call("PATCH", "/settings/wpm_target_max/", token, body={"value": 170})
    check("normal users cannot change settings (403)", status == 403, status)

    print("\nErrors")
    status, data = call("GET", "/recordings/999999/", token)
    check("unknown recording gives 404 in our error format", status == 404 and data["error"]["code"] == "not_found", status)
    status, data = call("POST", "/recordings/", token, multipart=make_multipart({}, "short.wav", silent_wav(3), "audio/wav"))
    check("a 3 second file is refused", status == 400 and data["error"]["code"] == "audio_too_short", status)
    status, data = call("POST", "/recordings/", token, multipart=make_multipart({}, "notes.txt", b"hello", "text/plain"))
    check("a .txt file is refused (415)", status == 415, status)

    print("\nClean up")
    status, _ = call("DELETE", "/recordings/%s/" % recording_id, token)
    check("delete the recording", status == 204, status)
    status, _ = call("GET", "/recordings/%s/" % recording_id, token)
    check("it is gone", status == 404, status)

    passed = sum(results)
    print("\n%s of %s checks passed." % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
