// 表示用の整形と、シートの値の読み取り（日付・数値）。legacy と同じ出力になるように書いてある
export const DAY = 864e5;

export function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => '&#' + c.charCodeAt(0) + ';');
}

// "1,565.15" や "-51.9%" を数値に。空欄は NaN
export function num(s) {
  s = (s || '').replace(/[,\s%]/g, '');
  return s === '' ? NaN : +s;
}

// "2007-10-09" / "2007/10/9" / "1871-01"（月次）を UTC のミリ秒に。読めなければ null
export function dt(s) {
  const m = (s || '').trim().replace(/\//g, '-').match(/^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?/);
  return m ? Date.UTC(+m[1], +m[2] - 1, +(m[3] || 1)) : null;
}

export const iso = (t) => new Date(t).toISOString().slice(0, 10);

// 2007年10月9日（monthOnly なら 2007年10月）
export function fdJa(t, monthOnly) {
  const d = new Date(t);
  return d.getUTCFullYear() + '年' + (d.getUTCMonth() + 1) + '月' + (monthOnly ? '' : d.getUTCDate() + '日');
}

// 2007/10/9
export function fdSlash(t) {
  const d = new Date(t);
  return d.getUTCFullYear() + '/' + (d.getUTCMonth() + 1) + '/' + d.getUTCDate();
}

export const year = (t) => new Date(t).getUTCFullYear();

// 日数 → 「45日」「8か月」「3年2か月」
export function dur(x) {
  if (x == null) return '—';
  if (x < 60) return Math.round(x) + '日';
  const m = Math.round(x / 30.44);
  return m < 24 ? m + 'か月' : Math.floor(m / 12) + '年' + (m % 12 ? (m % 12) + 'か月' : '');
}

// -0.519 → "-51.9%"（符号は負のときだけ）
export const pct = (x) => (x * 100).toFixed(1) + '%';
// 0.05 → "+5.0%"（正にも符号）
export const spct = (x) => (x > 0 ? '+' : '') + (x * 100).toFixed(1) + '%';

export function median(a) {
  a = a.slice().sort((x, y) => x - y);
  const n = a.length;
  return n ? (n % 2 ? a[(n - 1) / 2] : (a[n / 2 - 1] + a[n / 2]) / 2) : null;
}
