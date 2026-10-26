// Contract tests with a mocked DOM/Plotly API. These do not render a browser page.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const code = fs.readFileSync(path.join(__dirname, '../shadowvendor/utils/dashboard.js'), 'utf8');

async function environment(width, height, library = true) {
  const specs = [
    {id: 'vendor-distribution', kind: 'pie', total: 3, data: [{labels: ['A (2)', 'B (1)'], values: [2, 1]}]},
    {id: 'vlan-devices', kind: 'bar', data: [{x: ['VLAN 10'], y: [3]}]},
    {id: 'vlan-vendors', kind: 'bar', data: [{x: ['VLAN 10'], y: [2]}]},
    {id: 'vlan-distribution', kind: 'heatmap', data: [{x: ['Long manufacturer name for tick clipping'], y: ['VLAN 10'], z: [[3]]}]},
    {id: 'vlan-top-vendors', kind: 'stack', data: [{x: ['VLAN 10'], y: [3]}]}
  ];
  const nodes = new Map(specs.map(spec => [spec.id, {id: spec.id, clientWidth: width, clientHeight: height}]));
  nodes.set('chart-data', {textContent: JSON.stringify(specs)});
  nodes.set('chart-status', {hidden: false, textContent: ''});
  const buttons = ['vendor-distribution', 'vlan-top-vendors'].map(chart => ({
    dataset: {chart, series: '0'}, disabled: true, pressed: 'true', listeners: {},
    getAttribute() {return this.pressed;}, setAttribute(name, value) {this.pressed = value;},
    addEventListener(event, listener) {this.listeners[event] = listener;}
  }));
  const calls = [], frames = [], listeners = {};
  const Plotly = {
    newPlot(...args) {calls.push(['newPlot', ...args]); return Promise.resolve();},
    relayout(...args) {calls.push(['relayout', ...args]); return Promise.resolve();},
    restyle(...args) {calls.push(['restyle', ...args]); return Promise.resolve();}
  };
  const window = {Plotly: library ? Plotly : undefined, addEventListener(event, listener) {listeners[event] = listener;}};
  let resized;
  class ResizeObserver {constructor(callback) {resized = callback;} observe() {}}
  window.ResizeObserver = ResizeObserver;
  vm.runInNewContext(code, {window, Plotly, ResizeObserver,
    document: {getElementById: id => nodes.get(id), querySelectorAll: selector => selector.includes('data-chart=') ? buttons.slice(0, 1) : buttons},
    requestAnimationFrame: callback => frames.push(callback), console});
  await new Promise(resolve => setImmediate(resolve));
  const flush = () => {while (frames.length) frames.shift()();};
  flush();
  return {calls, nodes, buttons, frames, listeners, resized, flush};
}

(async () => {
  // Measured chart-container sizes representing narrow, wide and short layouts.
  for (const [width, height] of [[252,290],[322,350],[608,420],[430,290],[620,420],[900,360]]) {
    const env = await environment(width, height);
    assert.equal(env.calls.filter(call => call[0] === 'newPlot').length, 5);
    for (const call of env.calls) {
      const layout = call[3];
      assert.equal(layout.width, width);
      assert.equal(layout.height, height);
      assert.ok(width - layout.margin.l - layout.margin.r > 100);
      assert.ok(height - layout.margin.t - layout.margin.b > 80);
      assert.equal(call[4].responsive, true);
    }
    assert.equal(env.nodes.get('chart-status').hidden, true);
    const start = env.calls.length;
    env.resized(); env.resized(); env.listeners.resize();
    assert.equal(env.frames.length, 1);
    env.flush();
    assert.equal(env.calls.length, start); // no unchanged-size redraw loop
    env.nodes.get('vlan-devices').clientWidth = width + 50;
    env.nodes.get('vlan-devices').clientHeight = height + 30;
    env.resized(); env.flush();
    const update = env.calls.at(-1);
    assert.equal(update[0], 'relayout');
    assert.equal(update[2].width, width + 50);
    assert.equal(update[2].height, height + 30);
    assert.equal('xaxis.range' in update[2], false);
    env.buttons[0].listeners.click();
    assert.equal(env.buttons[0].pressed, 'false');
    assert.equal(JSON.stringify(env.calls.at(-1)[2].hiddenlabels), '["A (2)"]');
    env.buttons[1].listeners.click();
    assert.equal(env.calls.at(-1)[0], 'restyle');
    assert.equal(env.calls.at(-1)[2].visible, 'legendonly');
  }
  const offline = await environment(300, 300, false);
  assert.equal(offline.calls.length, 0);
  assert.equal(offline.nodes.get('chart-status').hidden, false);
  assert.match(offline.nodes.get('chart-status').textContent, /data tables/);
  assert.ok(offline.buttons.every(button => button.disabled));
  console.log('Passed: six container sizes, independent plots, coalesced resize, height changes, zoom preservation, legend toggles, and unavailable-library fallback. Mocked contracts only; no browser rendering.');
})().catch(error => {console.error(error); process.exitCode = 1;});
