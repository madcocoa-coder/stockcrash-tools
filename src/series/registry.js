// 系列の定義。ここに1件足せば読み込めるようにする（第3段階で米10年金利を追加する予定）
import { fetchText, pairs } from '../core/data.js';
import { iso } from '../core/format.js';
import sp500 from './sp500.js';

export const SERIES = { sp500 };

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
