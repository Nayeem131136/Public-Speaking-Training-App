// filler words, the transcript with fillers marked, and my own filler words
const FillerView = {
  render(a, transcript) {
    this.summary(a);
    this.transcript(a, transcript);
  },

  summary(a) {
    const box = $("filler-summary");
    box.textContent = "";
    const counts = a.fillers.by_word;
    const words = Object.keys(counts);
    if (!words.length) {
      box.appendChild(Fmt.el("p", "muted", "No filler words found."));
      return;
    }
    words.forEach((w) => box.appendChild(Fmt.el("span", "chip spot", w + " x " + counts[w])));
  },

  // mark the words that were found as fillers
  transcript(a, transcript) {
    const box = $("transcript");
    box.textContent = "";
    if (!transcript.words.length) {
      box.textContent = "(no words found)";
      return;
    }
    const hits = a.fillers.occurrences;
    transcript.words.forEach((w, i) => {
      if (i) box.appendChild(document.createTextNode(" "));
      const isFiller = hits.some((f) => w.start >= f.start_sec - 0.01 && w.end <= f.end_sec + 0.01);
      if (isFiller) {
        const mark = Fmt.el("mark", "", w.word);
        mark.title = "at " + Fmt.time(w.start);
        box.appendChild(mark);
      } else {
        box.appendChild(document.createTextNode(w.word));
      }
    });
  },

  // my filler words
  async loadMyWords() {
    const data = await Api.request("GET", "/filler-words/?page_size=100");
    const box = $("my-fillers");
    box.textContent = "";

    const list = Fmt.el("div");
    data.results.forEach((w) => {
      const chip = Fmt.el("span", "chip", w.word + " (" + w.language + (w.scope === "global" ? ", everyone" : ", mine") + ") ");
      if (w.scope === "personal" || (App.me && App.me.is_admin)) {
        const remove = Fmt.el("button", "link", "remove");
        remove.onclick = async () => {
          try {
            await Api.request("DELETE", "/filler-words/" + w.id + "/");
            this.loadMyWords();
          } catch (e) {
            App.message(e.message, "error");
          }
        };
        chip.appendChild(remove);
      }
      list.appendChild(chip);
    });
    box.appendChild(list);

    const row = Fmt.el("div", "row");
    const input = Fmt.el("input");
    input.placeholder = "Add a word or phrase, e.g. literally";
    input.id = "new-filler";
    const language = Fmt.el("select");
    language.id = "new-filler-language";
    language.appendChild(new Option("English", "en"));
    language.appendChild(new Option("Bangla", "bn"));
    const add = Fmt.el("button", "", "Add");
    add.id = "add-filler-btn";
    add.onclick = async () => {
      if (!input.value.trim()) return;
      try {
        await Api.request("POST", "/filler-words/", { json: { word: input.value, language: language.value } });
        this.loadMyWords();
      } catch (e) {
        App.message(e.message, "error");
      }
    };
    row.appendChild(input);
    row.appendChild(language);
    row.appendChild(add);
    box.appendChild(row);
    box.appendChild(Fmt.el("p", "muted", "Your own words are counted from your next recording."));
  },
};
