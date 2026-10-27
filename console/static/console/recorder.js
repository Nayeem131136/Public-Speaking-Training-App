// record from the microphone (or pick a file) and upload it
const Recorder = {
  recorder: null,
  stream: null,
  chunks: [],
  timer: null,
  blob: null,
  filename: "",

  init() {
    $("record-btn").onclick = () => this.start();
    $("stop-btn").onclick = () => this.stop();
    $("analyze-btn").onclick = () => this.upload();
    $("file-input").onchange = (e) => {
      if (e.target.files[0]) this.useFile(e.target.files[0]);
    };
  },

  // pick a format this browser can record
  pickType() {
    const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
    return types.find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported(t)) || "";
  },

  async start() {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      App.message("This browser can't record. Use Chrome, or choose a file instead.", "error");
      return;
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      App.message("Can't use the microphone. Allow it in the browser and try again.", "error");
      return;
    }

    const type = this.pickType();
    this.chunks = [];
    this.recorder = new MediaRecorder(this.stream, type ? { mimeType: type } : undefined);
    this.recorder.ondataavailable = (e) => {
      if (e.data.size) this.chunks.push(e.data);
    };
    this.recorder.onstop = () => this.finish(type);
    this.recorder.start();

    App.message("");
    $("record-btn").disabled = true;
    $("stop-btn").disabled = false;
    const startedAt = Date.now();
    const maxSeconds = App.settings.max_recording_seconds || 300;
    this.timer = setInterval(() => {
      const seconds = (Date.now() - startedAt) / 1000;
      $("timer").textContent = Fmt.time(seconds);
      if (seconds >= maxSeconds) this.stop();
    }, 250);
  },

  stop() {
    if (this.recorder && this.recorder.state !== "inactive") this.recorder.stop();
  },

  finish(type) {
    clearInterval(this.timer);
    this.stream.getTracks().forEach((t) => t.stop());
    $("record-btn").disabled = false;
    $("stop-btn").disabled = true;

    const mime = this.recorder.mimeType || type || "audio/webm";
    const ext = mime.includes("mp4") ? "mp4" : mime.includes("ogg") ? "ogg" : "webm";
    this.useBlob(new Blob(this.chunks, { type: mime }), "recording." + ext);
  },

  useFile(file) {
    this.useBlob(file, file.name);
  },

  useBlob(blob, name) {
    this.blob = blob;
    this.filename = name;
    $("file-name").textContent = name + " (" + Math.round(blob.size / 1024) + " KB)";
    if (window.URL && URL.createObjectURL) {
      $("preview").src = URL.createObjectURL(blob);
      $("preview").hidden = false;
    }
    $("analyze-btn").disabled = false;
    App.setStatus("Ready. Press Analyze. It must be between 10 seconds and 5 minutes.");
  },

  async upload() {
    if (!this.blob) return;
    const form = new FormData();
    form.append("audio", this.blob, this.filename);
    if ($("prompt-select").value) form.append("prompt_id", $("prompt-select").value);
    form.append("language", $("language-select").value);

    $("analyze-btn").disabled = true;
    App.setStatus("Uploading...");
    try {
      const rec = await Api.request("POST", "/recordings/", { form });
      await App.openRecording(rec.id);
    } catch (e) {
      App.setStatus(e.message, true);
    } finally {
      $("analyze-btn").disabled = false;
    }
  },
};
