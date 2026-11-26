// 系列の定義。ここに1件足せば読み込めるようにする
import { fetchText, pairs } from '../core/data.js';
import { iso } from '../core/format.js';
import sp500 from './sp500.js';
import ust10y from './ust10y.js';
import ff from './fedfunds.js';

export const SERIES = { sp500, ust10y, ff };

// 日付 t 時点の値（t 以前で最も新しい行）。月次の系列を日付で引くとき用
export function valueAt(rows, t) {
  let lo = 0, hi = rows.length - 1, v = null;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (rows[mid][0] <= t) { v = rows[mid][1]; lo = mid + 1; } else hi = mid - 1;
  }
  return v;
}

// 利上げ局面: 政策金利の谷から山までの上昇のうち、上げ幅が th（%pt）以上のもの。[[開始, 終了, 上げ幅], ...]
export function hikes(rows, th = 1) {
  const out = [];
  if (!rows.length) return out;
  let lo = rows[0], hi = rows[0], up = null; // up: 上昇中か（null は未定）
  for (const r of rows) {
    if (up !== false) {
      if (r[1] > hi[1]) hi = r;
      else if (hi[1] - r[1] >= th) { if (hi[1] - lo[1] >= th) out.push([lo[0], hi[0], hi[1] - lo[1]]); up = false; lo = r; }
    }
    if (up === false) {
      if (r[1] < lo[1]) lo = r;
      else if (r[1] - lo[1] >= th) { up = true; hi = r; }
    }
    if (up === null && r[1] < lo[1]) { lo = r; hi = r; }
  }
  if (up !== false && hi[1] - lo[1] >= th) out.push([lo[0], hi[0], hi[1] - lo[1]]);
  // 開始は「谷の水準（+0.25%pt 以内）を最後に出た月」にする（ゼロ金利が何年も続いた後の利上げを、上げ始めから数える）。
  // 3か月未満の上下は除く
  const DAY = 864e5;
  return out.map(([a, b, u]) => {
    const base = rows.find((x) => x[0] === a)[1];
    let s = a;
    for (const x of rows) { if (x[0] > b) break; if (x[0] >= a && x[1] <= base + 0.25) s = x[0]; }
    return [s, b, u];
  }).filter(([a, b]) => b - a >= 90 * DAY);
}

// 系列を [[t, v], ...]（v>0 の行だけ、日付順）で返す。
// range = [from, to]（ミリ秒）を渡すと、gviz のクエリで期間を絞って取る
export function loadSeries(sheet, def, freq, range) {
  const src = def.sources[freq];
  if (!src || src.type !== 'gviz') return Promise.reject(new Error('unknown source: ' + def.id + '/' + freq));
  let tq;
  if (range) {
    const [a, b] = src.cols || ['A', 'B'];
    tq = 'select ' + a + ',' + b + ' where ' + a + " >= date '" + iso(range[0]) + "' and " + a + " <= date '" + iso(range[1]) + "' order by " + a;
  }
  return fetchText(sheet, src.gid, tq).then((t) => pairs(t, src.date, src.value).filter((p) => p[0] != null && p[1] > 0).sort((x, y) => x[0] - y[0]));
}
