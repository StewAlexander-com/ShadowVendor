/* Inline report controller. No network requests beyond the existing Plotly script. */
(() => {
  "use strict";
  const status = document.getElementById("chart-status");
  const specs = JSON.parse(document.getElementById("chart-data").textContent);
  const fail = () => {
    status.hidden = false;
    status.textContent = "Charts could not load. Read the data tables below, or check your connection and reopen this report.";
  };
  if (!window.Plotly) { fail(); return; }
  const dimensions = new Map();
  const ready = new Set();
  const clip = value => String(value).length > 22 ? String(value).slice(0, 20) + "…" : String(value);
  function layout(spec, node) {
    const width = node.clientWidth;
    const height = node.clientHeight;
    const narrow = width < 480;
    const base = {
      width, height, autosize: true, showlegend: false,
      paper_bgcolor: "#192b36", plot_bgcolor: "#192b36",
      font: {family: "Arial, Helvetica, sans-serif", color: "#f7f3e9", size: 12},
      margin: {l: 54, r: 20, t: narrow ? 84 : 48, b: 72},
      hoverlabel: {bgcolor: "#101b25", bordercolor: "#b9dcd6", font: {color: "#f7f3e9"}},
      xaxis: {automargin: true, type: "category", tickangle: narrow ? -45 : 0,
              gridcolor: "#354953", linecolor: "#354953", tickfont: {color: "#bfccd3"}},
      yaxis: {automargin: true, rangemode: "tozero", dtick: 1,
              gridcolor: "#354953", zerolinecolor: "#354953", tickfont: {color: "#bfccd3"}},
      uirevision: "inventory", dragmode: "zoom"
    };
    if (!spec.data.length) {
      base.xaxis.visible = base.yaxis.visible = false;
      base.annotations = [{text: "No data available", x: .5, y: .5, xref: "paper", yref: "paper", showarrow: false}];
    } else if (spec.kind === "pie") {
      base.margin = {l: 16, r: 16, t: 48, b: 16};
      base.annotations = [{text: `<b>${spec.total.toLocaleString()}</b><br>total MACs`, x: .5, y: .5,
                            xref: "paper", yref: "paper", showarrow: false, font: {size: narrow ? 16 : 20}}];
    } else if (spec.kind === "heatmap") {
      base.margin.r = 64;
      base.margin.b = narrow ? 112 : 92;
      base.xaxis.tickangle = -45;
      base.xaxis.tickmode = "array";
      base.xaxis.tickvals = spec.data[0].x;
      base.xaxis.ticktext = spec.data[0].x.map(clip);
      base.yaxis.type = "category";
      delete base.yaxis.dtick;
    } else {
      base.yaxis.title = spec.id === "vlan-vendors" ? "Vendor labels" : "MAC addresses";
      const maximum = spec.kind === "stack"
        ? spec.data[0].y.reduce((largest, _, index) => Math.max(largest, spec.data.reduce((sum, trace) => sum + trace.y[index], 0)), 0)
        : spec.data.reduce((largest, trace) => trace.y.reduce((value, count) => Math.max(value, count), largest), 0);
      if (maximum > 10) delete base.yaxis.dtick;
      if (spec.kind === "stack") base.barmode = "stack";
    }
    return base;
  }
  let scheduled = false;
  function scheduleResize() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      for (const spec of specs) {
        if (!ready.has(spec.id)) continue;
        const node = document.getElementById(spec.id);
        const key = `${node.clientWidth}:${node.clientHeight}`;
        if (node.clientWidth <= 0 || dimensions.get(spec.id) === key) continue;
        dimensions.set(spec.id, key);
        const next = layout(spec, node);
        // Preserve zoom, legend selections and other user state while resizing.
        const update = {width: next.width, height: next.height, margin: next.margin,
                        "xaxis.tickangle": next.xaxis.tickangle};
        if (spec.kind === "pie") update.annotations = next.annotations;
        Plotly.relayout(node, update).catch(fail);
      }
    });
  }
  const observer = window.ResizeObserver ? new ResizeObserver(scheduleResize) : null;
  window.addEventListener("resize", scheduleResize, {passive: true});
  const config = {responsive: true, displaylogo: false, scrollZoom: false,
                  toImageButtonOptions: {format: "png", filename: "shadowvendor-analysis", scale: 2}};
  Promise.all(specs.map(spec => {
    const node = document.getElementById(spec.id);
    dimensions.set(spec.id, `${node.clientWidth}:${node.clientHeight}`);
    return Plotly.newPlot(node, spec.data, layout(spec, node), config).then(() => {
      ready.add(spec.id);
      if (observer) observer.observe(node);
    });
  })).then(() => {
    status.hidden = true;
    document.querySelectorAll("button[data-series]").forEach(button => {
      button.disabled = false;
      button.addEventListener("click", () => {
        const spec = specs.find(item => item.id === button.dataset.chart);
        const index = Number(button.dataset.series);
        const pressed = button.getAttribute("aria-pressed") !== "true";
        button.setAttribute("aria-pressed", String(pressed));
        const node = document.getElementById(spec.id);
        if (spec.kind === "pie") {
          const hidden = Array.from(document.querySelectorAll('button[data-chart="vendor-distribution"]'))
            .filter(item => item.getAttribute("aria-pressed") === "false")
            .map(item => spec.data[0].labels[Number(item.dataset.series)]);
          Plotly.relayout(node, {hiddenlabels: hidden}).catch(fail);
        } else {
          Plotly.restyle(node, {visible: pressed ? true : "legendonly"}, [index]).catch(fail);
        }
      });
    });
    scheduleResize();
  }).catch(fail);
})();
