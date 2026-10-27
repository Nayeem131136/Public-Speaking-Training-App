# Project log

One short entry for anything worth remembering: a decision and why, something that failed and how we fixed it, a challenge, what we found in a test. Newest at the bottom. Format: date, who, what.

## 13 Oct 2026 : backend skeleton

- The backend code (Django REST Framework, 5 apps, services, tests) was written with AI help (Claude), following our System Design. We are being open about that here on purpose.
- What was checked: all 118 tests pass. We also started the server and walked through the API by hand: register, login, upload, status, transcript, analysis, progress, filler words, settings, error messages, CORS.
- What was NOT checked: real Whisper on a real recording. Everything so far ran on the mock transcriber, which returns a fixed practice speech. Whether "um" and "uh" survive in a real transcript is still the biggest open question.
- Decision: if faster-whisper is not installed the project falls back to the mock instead of crashing (TRANSCRIBER=auto). The transcript endpoint says which engine was used.
- Decision: the starter filler list is built into the code and is used when the database has no global words.
- Next: everyone reads their own files (see backend/OWNERSHIP.md), runs them, and writes down what they changed or learned here.

## 14 Oct 2026 : errors, one-command start, test page

- Problem: the project gave errors on our laptops. Cause we could reproduce: the packages were pinned to exact versions and `pip install` failed on Python 3.9 ("No matching distribution"). Fix: requirements are now version ranges, so pip picks what fits the Python it runs on.
- We then ran the whole test suite on Python 3.9, 3.10, 3.11, 3.12, 3.13 and 3.14 (on Linux). All pass. We have NOT tried Windows ourselves, so other errors are possible there. If you get one, copy the first error line here.
- New: `python run.py` does everything (venv, install, database, Whisper model, server, opens Chrome). New: a test page at `/` where you can record or upload and see the result. It is for testing the backend, the real frontend is Group 7's job.
- Decision: if Whisper is installed but its model cannot be loaded (for example no internet), we fall back to the mock engine and show a warning on the page, instead of failing every upload. `TRANSCRIBER=faster-whisper` makes it strict.
- Checked: 120 unit tests, `try_api.py` (19 checks), and the test page clicked through in a simulated browser (login, topic, upload, result, filler words, history, delete).
- NOT checked: real Whisper transcription (the model could not be downloaded where we tested), recording from a real microphone in Chrome, and how the page looks in a real browser. These need a real run on a laptop with internet.
- Next: Tandra runs the first real Whisper test with her own voice and writes the result here.

## 16 Oct 2026 : "Could not transcribe the audio (transcription_failed)"

- Found from a screenshot: the recording and upload worked, the Whisper model loaded, but every transcription failed.
- Cause, reproduced: faster-whisper 1.2.1 cannot read any audio file with the newest `av` package (19.x): `open() got an unexpected keyword argument 'metadata_errors'`. We tried av 13, 15, 16, 17, 18 (all work) and 19 (fails). pip had installed the newest one.
- Fix: `requirements-whisper.txt` now says `av>=11,<19`. Running `python run.py` again downgrades it by itself (we tested that starting from av 19).
- Also added: a check of the audio decoder before Whisper is used (it falls back to the mock with a clear warning), and the real reason is now shown in the error message on the page.
- Not checked: the real transcription itself, because the model cannot be downloaded where we tested. The decoder part was tested with real webm files.
- Lesson: pin or cap packages that other packages depend on closely, and keep the first real error text, it saves hours.

