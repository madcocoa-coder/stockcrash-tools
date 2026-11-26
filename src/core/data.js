// Googleシート（gviz エンドポイント）からの取得・キャッシュ・CSV解析
import { dt, num } from './format.js';

export const DEFAULT_SHEET = '1JP-4PJimOphXB9pTvG8xCW4F12Jn5FrnHVUiT4iRVFM';
export const TABS = { events: 257873827, monthly: 886500007, daily: 2091119745 };

export function gvizUrl(sheet, gid, tq) {
  return 'https://docs.google.com/spreadsheets/d/' + sheet + '/gviz/tq?tqx=out:csv&gid=' + gid +
    (tq ? '&tq=' + encodeURIComponent(tq) : '');
}

// 同じURLはページ内で1回だけ取りに行く（失敗したら次回やり直す）
const cache = new Map();
export function fetchText(sheet, gid, tq) {
  const u = gvizUrl(sheet, gid, tq);
  if (!cache.has(u)) {
    const p = fetch(u, { cache: 'no-store' }).then((r) => {
      if (!r.ok) throw r.status;
      return r.text();
    });
    p.catch(() => cache.delete(u));
    cache.set(u, p);
  }
  return cache.get(u);
}

export function csv(t) {
  const o = [];
  let r = [], f = '', q = false;
  t = t.replace(/\r/g, '');
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (q) {
      if (c == '"') {
        if (t[i + 1] == '"') { f += '"'; i++; } else q = false;
      } else f += c;
    } else if (c == '"') q = true;
    else if (c == ',') { r.push(f); f = ''; }
    else if (c == '\n') { r.push(f); o.push(r); r = []; f = ''; }
    else f += c;
  }
  if (f || r.length) { r.push(f); o.push(r); }
  return o;
}

// 見出し名で列を探す表。cols は {キー: 見出し名}。見つからない列は -1
export function table(text, cols) {
  const rows = csv(text), head = rows.shift() || [], ix = {};
  for (const k in cols) ix[k] = head.indexOf(cols[k]);
  return { rows, ix };
}

// 日付・値の2列を [[t, v], ...] に。見出しが見つからなければ1列目・2列目
export function pairs(text, dateCol, valueCol) {
  const { rows, ix } = table(text, { d: dateCol, v: valueCol });
  const di = ix.d < 0 ? 0 : ix.d, vi = ix.v < 0 ? 1 : ix.v;
  return rows.map((r) => [dt(r[di]), num(r[vi])]);
}
