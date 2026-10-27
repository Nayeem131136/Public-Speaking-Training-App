// main page: login, topics, history and showing the result
const App = {
  me: null,
  settings: {},
  pollTimer: null,

  async start() {
    $("login-btn").onclick = () => this.login(false);
    $("register-btn").onclick = () => this.login(true);
    $("logout-btn").onclick = () => this.logout();
    $("prompt-select").onchange = () => this.showPrompt();
    $("password").onkeydown = (e) => {
      if (e.key === "Enter") this.login(false);
    };
    Recorder.init();

    if (Api.token) {
      try {
        await this.enter();
        return;
      } catch (e) {
        Api.setToken("");
      }
    }
    this.showLogin();
  },

  message(text, kind) {
    const box = $("message");
    box.textContent = text || "";
    box.className = "message" + (kind ? " " + kind : "");
    box.hidden = !text;
  },

  setStatus(text, isError) {
    $("status").textContent = text;
    $("status").style.color = isError ? "#E4572E" : "";
  },

  showLogin() {
    $("login-card").hidden = false;
    $("app").hidden = true;
    $("user-box").hidden = true;
  },

  async login(register) {
    const username = $("username").value.trim();
    const password = $("password").value;
    if (!username || !password) {
      this.message("Type a username and a password in the two boxes first, then press the button again.", "error");
      (username ? $("password") : $("username")).focus();
      return;
    }
    try {
      if (register) await Api.request("POST", "/auth/register/", { json: { username, password } });
      const data = await Api.request("POST", "/auth/login/", { json: { username, password } });
      Api.setToken(data.access);
      await this.enter();
      this.message(register ? "Account created. You are logged in." : "", register ? "ok" : "");
    } catch (e) {
      this.message(e.message, "error");
    }
  },

  logout() {
    Api.setToken("");
    clearTimeout(this.pollTimer);
    $("result-card").hidden = true;
    this.showLogin();
  },

  async enter() {
    this.me = await Api.request("GET", "/auth/me/");
    $("user-name").textContent = this.me.username + (this.me.is_admin ? " (admin)" : "");
    $("user-box").hidden = false;
    $("login-card").hidden = true;
    $("app").hidden = false;
    this.message("");
    this.settings = await Api.request("GET", "/settings/");
    await this.loadPrompts();
    await this.loadHistory();
    await FillerView.loadMyWords();
  },

  // topics
  async loadPrompts() {
    const data = await Api.request("GET", "/prompts/?page_size=100");
    const select = $("prompt-select");
    select.textContent = "";
    select.appendChild(new Option("No topic (free speech)", ""));
    const groups = {};
    data.results.forEach((p) => {
      if (!groups[p.category_name]) {
        groups[p.category_name] = document.createElement("optgroup");
        groups[p.category_name].label = p.category_name;
        select.appendChild(groups[p.category_name]);
      }
      const option = new Option(p.title, p.id);
      option.dataset.text = p.text;
      groups[p.category_name].appendChild(option);
    });
    this.showPrompt();
  },

  showPrompt() {
    const option = $("prompt-select").selectedOptions[0];
    $("prompt-text").textContent = option && option.dataset.text ? option.dataset.text : "";
    $("prompt-text").hidden = !$("prompt-text").textContent;
  },

  // past recordings
  async loadHistory() {
    const data = await Api.request("GET", "/recordings/?page_size=20");
    const box = $("history");
    box.textContent = "";
    if (!data.results.length) {
      box.appendChild(Fmt.el("p", "muted", "Nothing yet. Record something above."));
      return;
    }
    data.results.forEach((rec) => {
      const row = Fmt.el("div", "list-item");
      let info = "#" + rec.id + "  " + new Date(rec.created_at).toLocaleString() + "  " + rec.status;
      if (rec.summary) info += "  " + rec.summary.wpm + " wpm, " + rec.summary.filler_count + " fillers";
      row.appendChild(Fmt.el("span", "", info));

      const buttons = Fmt.el("span");
      const open = Fmt.el("button", "small", "Open");
      open.onclick = () => this.openRecording(rec.id);
      const del = Fmt.el("button", "small", "Delete");
      del.onclick = async () => {
        if (!confirm("Delete recording #" + rec.id + "?")) return;
        await Api.request("DELETE", "/recordings/" + rec.id + "/");
        if (this.shown === rec.id) $("result-card").hidden = true;
        this.loadHistory();
      };
      buttons.appendChild(open);
      buttons.appendChild(del);
      row.appendChild(buttons);
      box.appendChild(row);
    });
  },

  // wait for the result, then show it
  async openRecording(id) {
    clearTimeout(this.pollTimer);
    const started = Date.now();
    const check = async () => {
      let rec;
      try {
        rec = await Api.request("GET", "/recordings/" + id + "/");
      } catch (e) {
        this.setStatus(e.message, true);
        return;
      }
      if (rec.status === "processing") {
        if (Date.now() - started > 5 * 60 * 1000) {
          this.setStatus("Still processing after 5 minutes. Look at the server window for errors.", true);
          return;
        }
        this.setStatus("Processing recording #" + id + "... the first time Whisper can be slow.");
        this.pollTimer = setTimeout(check, 2000);
        return;
      }
      if (rec.status === "failed") {
        this.setStatus(rec.error.message + " (" + rec.error.code + ")", true);
        this.loadHistory();
        return;
      }
      await this.showResult(id);
    };
    await check();
  },

  async showResult(id) {
    const analysis = await Api.request("GET", "/recordings/" + id + "/analysis/");
    const transcript = await Api.request("GET", "/recordings/" + id + "/transcript/");
    this.shown = id;

    const note = $("engine-note");
    note.hidden = transcript.engine !== "mock";
    note.textContent =
      "This result is from the MOCK engine. It is a fixed practice speech, not your voice. " +
      "Whisper is not installed or not ready yet. Stop the server and start it again with: python run.py";

    PaceView.render(analysis);
    FillerView.render(analysis, transcript);
    $("result-card").hidden = false;
    $("result-card").scrollIntoView({ behavior: "smooth" });
    this.setStatus("Done. Recording #" + id);
    this.loadHistory();
  },
};

window.addEventListener("DOMContentLoaded", () => App.start());
