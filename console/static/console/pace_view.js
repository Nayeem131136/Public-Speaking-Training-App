// the pace numbers, the pace chart and the pauses
const PaceView = {
  texts: { within_target: "On target", too_slow: "A bit slow", too_fast: "A bit fast", no_speech: "No speech found" },
  classes: { within_target: "good", too_slow: "watch", too_fast: "watch", no_speech: "watch" },

  render(a) {
    this.tiles(a);
    this.chart(a);
    this.pauses(a);
  },

  tile(label, value, sub, chipText, chipClass) {
    const box = Fmt.el("div", "tile");
    box.appendChild(Fmt.el("div", "label", label));
    box.appendChild(Fmt.el("div", "value", String(value)));
    box.appendChild(Fmt.el("div", "sub", sub));
    if (chipText) box.appendChild(Fmt.el("span", "chip " + chipClass, chipText));
    return box;
  },

  tiles(a) {
    const s = a.summary;
    const status = a.pacing.status;
    const box = $("tiles");
    box.textContent = "";
    box.appendChild(this.tile("Pace", s.wpm, "words per minute", this.texts[status], this.classes[status]));
    box.appendChild(this.tile("Words", s.total_words, "in " + Fmt.time(a.duration_sec)));
    box.appendChild(this.tile("Filler words", s.filler_count, "found"));
    box.appendChild(this.tile("Pauses", s.pause_count, "longest " + s.longest_pause_sec + " s"));
  },

  chart(a) {
    const box = $("pace-chart");
    box.textContent = "";
    const segments = a.pacing.segments;
    if (!segments.length) {
      box.appendChild(Fmt.el("p", "muted", "Not enough speech for a chart."));
      return;
    }

    const min = a.pacing.target_min;
    const max = a.pacing.target_max;
    const top = Math.max(max * 1.3, ...segments.map((s) => s.wpm * 1.15));

    const wrap = Fmt.el("div", "chart-wrap");
    const chart = Fmt.el("div", "chart");
    const band = Fmt.el("div", "band");
    band.style.bottom = (min / top) * 100 + "%";
    band.style.height = ((max - min) / top) * 100 + "%";
    chart.appendChild(band);

    segments.forEach((s) => {
      const bar = Fmt.el("div", "bar");
      bar.style.height = (s.wpm / top) * 100 + "%";
      if (s.wpm < min || s.wpm > max) bar.style.background = "#E4572E";
      bar.appendChild(Fmt.el("span", "top", String(Math.round(s.wpm))));
      bar.appendChild(Fmt.el("span", "time", Fmt.time(s.start_sec)));
      chart.appendChild(bar);
    });
    wrap.appendChild(chart);
    box.appendChild(wrap);

    const size = Math.round(segments[0].end_sec - segments[0].start_sec);
    box.appendChild(
      Fmt.el("div", "legend", "Each bar is about " + size + " seconds. The green band is the target, " + min + " to " + max + " words per minute.")
    );
  },

  pauses(a) {
    const box = $("pauses");
    box.textContent = "";
    if (!a.pauses.length) {
      box.appendChild(Fmt.el("p", "muted", "No pauses found."));
      return;
    }
    const table = Fmt.el("table");
    const head = Fmt.el("tr");
    ["At", "Length", "Kind"].forEach((h) => head.appendChild(Fmt.el("th", "", h)));
    table.appendChild(head);

    const kinds = { short: "", dramatic: "good", long: "watch" };
    a.pauses.slice(0, 30).forEach((p) => {
      const row = Fmt.el("tr");
      row.appendChild(Fmt.el("td", "", Fmt.time(p.start_sec)));
      row.appendChild(Fmt.el("td", "", p.duration_sec + " s"));
      const kind = Fmt.el("td");
      kind.appendChild(Fmt.el("span", "chip " + kinds[p.kind], p.kind));
      row.appendChild(kind);
      table.appendChild(row);
    });
    box.appendChild(table);
    if (a.pauses.length > 30) box.appendChild(Fmt.el("p", "muted", "Showing the first 30 of " + a.pauses.length + "."));
  },
};
