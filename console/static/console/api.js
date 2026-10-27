// talks to the backend
const $ = (id) => document.getElementById(id);

class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const Fmt = {
  // 75 -> "1:15"
  time(sec) {
    const total = Math.round(sec);
    return Math.floor(total / 60) + ":" + String(total % 60).padStart(2, "0");
  },
  el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  },
};

const Api = {
  base: "/api/v1",
  token: localStorage.getItem("bs_token") || "",

  setToken(token) {
    this.token = token || "";
    if (token) localStorage.setItem("bs_token", token);
    else localStorage.removeItem("bs_token");
  },

  async request(method, path, options = {}) {
    const headers = {};
    let body;
    if (this.token) headers["Authorization"] = "Bearer " + this.token;
    if (options.json) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.json);
    }
    if (options.form) body = options.form;

    let response;
    try {
      response = await fetch(this.base + path, { method, headers, body });
    } catch (e) {
      throw new ApiError("Cannot reach the server. Is it running?", 0, "network");
    }

    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (e) {
      data = null;
    }

    if (!response.ok) {
      const err = data && data.error ? data.error : {};
      let message = err.message || "Something went wrong (" + response.status + ")";
      if (err.fields) {
        // show the first field problem, e.g. "password: This password is too common."
        const name = Object.keys(err.fields)[0];
        const first = [].concat(err.fields[name])[0];
        message = name + ": " + first;
      }
      if (response.status === 401 && this.token && path.indexOf("/auth/") !== 0) {
        // the token ran out, start again from the login box
        this.setToken("");
        App.message("Your session ended. Please log in again.", "error");
        App.showLogin();
      }
      throw new ApiError(message, response.status, err.code || "error");
    }
    return data;
  },
};
