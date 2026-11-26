// SVG描画の共通部品（文字列で組み立てる。外部ライブラリなし）

// 属性は書いた順に出す。null / undefined / false の属性は出さない
export function el(tag, attrs, body) {
  let s = '<' + tag;
  for (const k in attrs) {
    const v = attrs[k];
    if (v != null && v !== false) s += ' ' + k + '="' + v + '"';
  }
  return body == null ? s + '/>' : s + '>' + body + '</' + tag + '>';
}

export const f1 = (v) => v.toFixed(1);

export function svg(W, H, label, body) {
  return '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + label + '">' + body + '</svg>';
}

// 折れ線の d 属性
export function pathD(pts, X, Y) {
  let d = '';
  pts.forEach((p, i) => { d += (i ? 'L' : 'M') + f1(X(p[0])) + ' ' + f1(Y(p[1])); });
  return d;
}

// 横の目盛り線＋左のラベル
export function yGrid(y, x1, x2, label, o = {}) {
  return el('line', { x1, x2, y1: y, y2: y, stroke: o.stroke || '#eee', 'stroke-width': o.width }) +
    el('text', { x: x1 - (o.pad || 4), y, dy: 4, 'font-size': 10, 'text-anchor': 'end', fill: o.fill || '#888' }, label);
}

// 縦の目盛り線＋下のラベル
export function xGrid(x, y1, y2, ly, label, o = {}) {
  return el('line', { x1: x, x2: x, y1, y2, stroke: o.stroke || '#f3f3f3' }) +
    el('text', { x, y: ly, 'font-size': 10, 'text-anchor': 'middle', fill: o.fill || '#888' }, label);
}

// 対数軸の目盛り（1・2・5 刻み。範囲が広いときは 10 のべきだけ）
export function logTicks(lo, hi) {
  const o = [];
  for (let k = Math.floor(lo); k <= Math.ceil(hi); k++) {
    [1, 2, 5].forEach((f) => {
      const v = f * Math.pow(10, k), l = Math.log10(v);
      if (l < lo || l > hi) return;
      if (f != 1 && hi - lo > 2.2) return;
      o.push(v);
    });
  }
  return o;
}

// 年の目盛り間隔
export const yearStep = (span) => (span > 100 ? 20 : span > 50 ? 10 : span > 25 ? 5 : 2);

// 区間 [lo, hi] を step 刻みで（浮動小数の誤差を吸収）
export function steps(lo, hi, step) {
  const o = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) o.push(v);
  return o;
}

// リサイズ時に描き直す（150ms まとめる）
export function onResize(fn) {
  let t;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(fn, 150); });
}
