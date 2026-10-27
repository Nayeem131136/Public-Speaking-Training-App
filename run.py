"""Start Backstage with one command:  python run.py

The first time it makes a virtual environment, installs everything, sets up
the database and downloads the Whisper model. After that it starts the server
and opens Chrome.

  python run.py               set up and start
  python run.py test          run the tests
  python run.py check         start the server and run try_api.py against it
  python run.py analyze x.wav test Whisper on one audio file
  --no-whisper                don't install Whisper (the mock engine is used)
  --no-browser                don't open the browser
"""
import argparse
import hashlib
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

BASE = Path(__file__).resolve().parent
VENV = BASE / "venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def say(text=""):
    print(text, flush=True)


def python_version(command):
    # ask a python command which version it is, None if it doesn't work
    try:
        out = subprocess.run(
            command + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            capture_output=True, text=True, timeout=15,
        )
        major, minor = out.stdout.split()
        return int(major), int(minor)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def find_python():
    # 3.10 to 3.13 works best with everything (Django and Whisper)
    def good(v):
        return v is not None and (3, 10) <= v <= (3, 13)

    if good(sys.version_info[:2]):
        return [sys.executable]
    for command in (["py", "-3.12"], ["py", "-3.11"], ["py", "-3.13"], ["py", "-3.10"],
                    ["python3.12"], ["python3.11"], ["python3.13"], ["python3.10"]):
        if good(python_version(command)):
            return command
    if sys.version_info >= (3, 9):
        return [sys.executable]
    sys.exit("Python 3.9 or newer is needed. Install Python 3.12 from python.org and run this again.")


def make_venv():
    if VENV_PYTHON.exists():
        return
    command = find_python()
    say("Making the virtual environment (venv) with: " + " ".join(command))
    result = subprocess.run(command + ["-m", "venv", str(VENV)])
    if result.returncode != 0 or not VENV_PYTHON.exists():
        sys.exit("Could not make the virtual environment. Delete the 'venv' folder, then try again.")


def pip_install(requirements, stamp_name):
    # skip when the requirements file did not change since the last install
    stamp = VENV / stamp_name
    digest = hashlib.sha256((BASE / requirements).read_bytes()).hexdigest()
    if stamp.exists() and stamp.read_text() == digest:
        return True
    say("Installing %s (can take a few minutes the first time)..." % requirements)
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check", "--upgrade", "pip"],
                   capture_output=True)
    result = subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check", "-r", requirements],
                            cwd=BASE)
    if result.returncode != 0:
        return False
    stamp.write_text(digest)
    return True


def manage(*args, capture=False, env=None):
    full_env = dict(os.environ, PYTHONUTF8="1", **(env or {}))
    return subprocess.run([str(VENV_PYTHON), "manage.py", *args], cwd=BASE, env=full_env,
                          capture_output=capture, text=capture)


def setup(use_whisper):
    make_venv()
    if not pip_install("requirements.txt", ".installed_base"):
        sys.exit("\nInstalling the requirements failed. Check your internet connection and read the error above.\n"
                 "If it says 'No matching distribution', your Python is too old: install Python 3.12 and delete the venv folder.")

    result = manage("migrate", "--noinput", capture=True)
    if result.returncode != 0:
        sys.exit("Database setup failed:\n" + result.stdout + result.stderr)
    manage("seed_demo", capture=True)

    if not use_whisper:
        return
    if not pip_install("requirements-whisper.txt", ".installed_whisper"):
        say("\nWARNING: could not install Whisper. The mock engine will be used (fixed practice speech).")
        say("Try again later with internet, or use: python run.py --no-whisper\n")
        return
    ready = VENV / ".model_ready"
    if not ready.exists():
        say("Getting the Whisper model (about 150 MB the first time, needs internet)...")
        if manage("prepare_whisper").returncode == 0:
            ready.write_text("ok")
        else:
            say("\nWARNING: the Whisper model is not ready. Results will say 'mock' until it is.")
            say("Connect to the internet and run python run.py again.\n")


def free_port(start=8000):
    for port in range(start, start + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    sys.exit("No free port found between %d and %d." % (start, start + 19))


def start_server(port):
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.Popen([str(VENV_PYTHON), "manage.py", "runserver", "127.0.0.1:%d" % port, "--noreload"],
                            cwd=BASE, env=env)


def wait_until_up(process, port, seconds=90):
    end = time.time() + seconds
    while time.time() < end:
        if process.poll() is not None:
            sys.exit("The server stopped. Read the error above.")
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    sys.exit("The server did not start in time.")


def open_in_chrome(url):
    candidates = []
    if os.name == "nt":
        for name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            folder = os.environ.get(name)
            if folder:
                candidates.append(Path(folder) / "Google/Chrome/Application/chrome.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            for folder in os.environ.get("PATH", "").split(os.pathsep):
                candidates.append(Path(folder) / name)
    for path in candidates:
        if path.exists():
            subprocess.Popen([str(path), url])
            return
    webbrowser.open(url)  # no Chrome found, use the default browser


def main():
    parser = argparse.ArgumentParser(description="Start Backstage")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "test", "check", "analyze"])
    parser.add_argument("--no-whisper", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args, extra = parser.parse_known_args()
    # a file path typed next to run.py should work from any folder
    extra = [str(Path(a).resolve()) if Path(a).exists() else a for a in extra]

    setup(use_whisper=not args.no_whisper and args.command in ("run", "check", "analyze"))

    if args.command == "test":
        sys.exit(manage("test").returncode)
    if args.command == "analyze":
        sys.exit(manage("analyze_file", *extra).returncode)

    port = free_port()
    server = start_server(port)
    url = "http://127.0.0.1:%d/" % port
    try:
        wait_until_up(server, port)
        if args.command == "check":
            env = dict(os.environ, BACKSTAGE_URL=url.rstrip("/"), PYTHONUTF8="1")
            sys.exit(subprocess.run([str(VENV_PYTHON), "try_api.py"], cwd=BASE, env=env).returncode)

        say("\n" + "=" * 60)
        say("Backstage is running:  " + url)
        say("Admin panel:           " + url + "admin/   (make a login first: python manage.py createsuperuser)")
        say("Stop it with Ctrl+C in this window.")
        say("=" * 60 + "\n")
        if not args.no_browser:
            open_in_chrome(url)
        server.wait()
    except KeyboardInterrupt:
        say("\nStopping...")
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    main()
