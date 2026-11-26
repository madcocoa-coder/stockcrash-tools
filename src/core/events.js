// 「暴落一覧」タブの正規化と派生値
import { DAY, esc, num, dt } from './format.js';
import { fetchText, table, TABS } from './data.js';

const COLS = { id: 'ID', n: '名称', pd: 'ピーク日', pv: 'ピーク値', td: '底日', tv: '底値', rd: '回復日', g: 'グループ', gr: 'データ' };

// 1行 = 1つの暴落。name / grp はHTMLエスケープ済み
export function parseEvents(text) {
  const { rows, ix: I } = table(text, COLS), out = [];
  rows.forEach((r) => {
    const pk = dt(r[I.pd]), tr = dt(r[I.td]), pv = num(r[I.pv]), tv = num(r[I.tv]);
    if (!pk || !tr || !(pv > 0) || !(tv > 0)) return;
    const rc = dt(r[I.rd]), dd = tv / pv - 1;
    out.push({
      id: r[I.id], name: esc(r[I.n]), pk, tr, rc, pv, tv, dd,
      bear: dd <= -0.2, // 弱気相場（-20%以上）か、調整（-10〜20%）か
      grp: esc(r[I.g] || ''),
      mon: (r[I.gr] || '').indexOf('月次') >= 0, // 1927年以前の月次平均の行
      on: !rc, // 継続中（未回復）
      fall: (tr - pk) / DAY,
      rec: rc ? (rc - tr) / DAY : null,
      tot: rc ? (rc - pk) / DAY : null,
    });
  });
  return out;
}

const loaded = new Map();
export function loadEvents(sheet) {
  if (!loaded.has(sheet)) {
    const p = fetchText(sheet, TABS.events).then(parseEvents);
    p.catch(() => loaded.delete(sheet));
    loaded.set(sheet, p);
  }
  return loaded.get(sheet);
}

// チップや自動文で使う短い名前。「2007〜09年 世界金融危機（リーマン・ショック）」→「リーマン・ショック」
export function shortName(e) {
  if (e && e.on) return '今回';
  const b = e.name.replace(/^\d{4}(〜\d{2,4})?年\s*/, ''), m = b.match(/（(.*?)）/);
  if (m) {
    if (/ショック/.test(m[1])) return m[1];
    return b.replace(/（.*?）/g, '');
  }
  return b;
}
