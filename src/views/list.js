// 一覧ビュー: S&P500の対数チャート＋下落期間の帯＋回復までのタイムライン＋統計＋表
import { DAY, fdJa, dur, pct, median } from '../core/format.js';
import { loadEvents } from '../core/events.js';
import { SERIES, loadSeries } from '../series/registry.js';
import { segHTML, bindSeg } from '../ui/controls.js';
import { el, f1, svg, pathD, yGrid, xGrid, logTicks, yearStep, onResize } from '../ui/chart.js';
import { addFullscreen, fitHeight } from '../ui/fullscreen.js';

const CLS = [['all', 'すべて'], ['bear', '暴落 -20%〜'], ['corr', '調整 -10〜20%']];
const FROM = [['1871', '1871年〜'], ['1928', '1928年〜'], ['1970', '1970年〜'], ['2000', '2000年〜']];
const COLS = [['name', '出来事'], ['dd', '下落率'], ['pk', 'ピーク'], ['tr', '底'], ['fall', '下落期間'], ['rec', '回復期間'], ['tot', '全期間'], ['rc', '回復日']];
const INFO0 = '帯や表の行をタップすると詳細を表示';
const ERR = '<div class="ch-note">データを読み込めませんでした。時間をおいて再読み込みしてください。</div>';

const HTML =
  '<div class="ch-ctl"><span class="ch-lab">対象</span>' + segHTML('ch-seg', 'cls', CLS, 'all') +
  '<span class="ch-lab">期間</span>' + segHTML('ch-seg', 'from', FROM, '1871') + '</div>' +
  '<div class="ch-upd ch-lab"></div><div class="ch-stats"></div>' +
  '<div class="ch-fig"><div class="ch-chart"><div class="ch-note">データを読み込み中…</div></div>' +
  '<div class="ch-leg"><span><i style="background:var(--bear)"></i>暴落の下落期間（ピーク→底）</span>' +
  '<span><i style="background:var(--corr)"></i>調整の下落期間</span>' +
  '<span><i style="background:var(--bear);opacity:.25"></i>回復期間（下段、点線は未回復）</span>' +
  '<span><i style="background:var(--line);height:2px;vertical-align:3px"></i>S&amp;P500（対数目盛）</span></div>' +
  '<div class="ch-info">' + INFO0 + '</div></div>' + // .ch-fig まで（全画面の範囲）
  '<div class="ch-act"></div>' + // 選んだ暴落を比較タブへ送るボタン（タブ統合時だけ出す）
  '<div class="ch-ctl"><input type="search" placeholder="名称で絞り込み（例：ショック）"><span class="ch-lab">見出しをタップで並び替え</span></div>' +
  '<div class="ch-wrap"><table><thead><tr>' + COLS.map(([k, l]) => '<th data-s="' + k + '">' + l + '</th>').join('') +
  '</tr></thead><tbody></tbody></table></div>' +
  '<div class="ch-note">S&amp;P500の終値ベース（配当含まず・インフレ調整なし）。1927年以前はShillerの月次平均値。' +
  '回復＝ピークの値を終値で取り戻した日。暴落（20%以上の下落）は底から20%以上戻したら終わりとみなして区切る。出典：Robert Shiller、Yahoo Finance、Morningstar。</div>';

const tag = (e) => '<span class="tag ' + (e.bear ? 'b' : 'c') + '">' + (e.bear ? '暴落' : '調整') + '</span>';
const ongo = '<span class="ongo">未回復</span>';
const col = (e) => (e.bear ? 'var(--bear)' : 'var(--corr)');

export function mountList(host, { sheet, onCompare }) {
  host.innerHTML = '<div class="ch-root">' + HTML + '</div>';
  const R = host.firstChild, $ = (s) => R.querySelector(s);
  const st = { cls: 'all', from: 1871, sort: 'pk', dir: 1, q: '', sel: null };
  let EV = [], PX = [];
  const fs = addFullscreen($('.ch-fig'), () => chart());

  Promise.all([loadEvents(sheet), loadSeries(sheet, SERIES.sp500, 'monthly')])
    .then(([ev, px]) => { EV = ev.map((e) => ({ ...e })); PX = px; init(); })
    .catch(() => { $('.ch-chart').innerHTML = ERR; });

  function init() {
    R.querySelectorAll('.ch-seg').forEach((s) => bindSeg(s, (v) => {
      const k = s.dataset.k;
      st[k] = k == 'from' ? +v : v;
      draw();
    }));
    $('input[type=search]').addEventListener('input', function () { st.q = this.value.trim(); table(); });
    R.querySelectorAll('th').forEach((th) => th.addEventListener('click', () => {
      const s = th.dataset.s;
      st.dir = st.sort == s ? -st.dir : s == 'dd' || s == 'name' ? 1 : -1;
      if (s == 'pk' && st.sort != 'pk') st.dir = 1;
      st.sort = s;
      table();
    }));
    onResize(chart);
    if (PX.length) $('.ch-upd').textContent = 'データ：S&P500終値ベース・' + fdJa(PX[PX.length - 1][0], true) + 'まで反映（Googleシートから自動更新）';
    draw();
  }

  // 対象・期間で絞った暴落（期間の開始より後に回復した＝期間内に見えているもの）
  function vis() {
    const f = Date.UTC(st.from, 0, 1);
    return EV.filter((e) => (st.cls == 'all' || (st.cls == 'bear') == e.bear) && (e.rc || Infinity) >= f);
  }

  function draw() { stats(); chart(); table(); }

  function stats() {
    const v = vis(), done = v.filter((e) => e.rc), on = v.filter((e) => !e.rc);
    const w = v.reduce((a, e) => (!a || e.dd < a.dd ? e : a), null);
    const tiles = [
      [v.length + '回', '件数'],
      [v.length ? pct(v.reduce((s, e) => s + e.dd, 0) / v.length) : '—', '平均下落率'],
      [dur(median(v.map((e) => e.fall))), '下落期間（中央値）'],
      [dur(median(done.map((e) => e.rec))), '回復期間（中央値）'],
      [w ? pct(w.dd) : '—', w ? '最大: ' + w.name : '最大下落'],
    ];
    $('.ch-stats').innerHTML = tiles.map((s) => '<div class="ch-stat"><b>' + s[0] + '</b><span>' + s[1] + '</span></div>').join('') +
      (on.length ? '<div class="ch-stat"><b class="ongo">' + on.length + '件</b><span>継続中: ' + on.map((e) => e.name).join('、') + '</span></div>' : '');
  }

  function chart() {
    const box = $('.ch-chart'), W = Math.max(320, box.clientWidth || 800), mob = W < 560;
    const m = { l: mob ? 38 : 50, r: 10, t: 10, b: 24 };
    const x0 = Date.UTC(st.from, 0, 1), x1 = Math.max(PX.length ? PX[PX.length - 1][0] : Date.now(), Date.now() - 30 * DAY);
    const pts = PX.filter((p) => p[0] >= x0);
    if (!pts.length) { box.innerHTML = ''; return; }
    let lo = Infinity, hi = 0;
    pts.forEach((p) => { lo = Math.min(lo, p[1]); hi = Math.max(hi, p[1]); });
    lo = Math.log10(lo * 0.85); hi = Math.log10(hi * 1.15);

    // タイムラインのレーン分け（前の暴落の回復前に次が始まったら下のレーンへ）
    const ev = vis().slice().sort((a, b) => a.pk - b.pk), ends = [];
    ev.forEach((e) => {
      let L = 0;
      while (ends[L] != null && ends[L] >= e.pk) L++;
      ends[L] = e.rc || x1;
      e._ln = L;
    });
    const LH = mob ? 6 : 7, TL = ends.length * (LH + 2) + 18;
    // 全画面中は画面の高さに合わせる（下段のタイムライン分を引く）
    const PH = fs.isFull() ? Math.max(200, fitHeight($('.ch-fig'), box, 200) - TL) : mob ? 300 : 400, H = PH + TL, bot = PH - m.b;
    const X = (t) => m.l + (t - x0) / (x1 - x0) * (W - m.l - m.r);
    const Y = (v) => m.t + (hi - Math.log10(v)) / (hi - lo) * (PH - m.t - m.b);

    let s = '';
    logTicks(lo, hi).forEach((v) => { s += yGrid(f1(Y(v)), m.l, W - m.r, v.toLocaleString()); });
    const y0 = new Date(x0).getUTCFullYear(), y1 = new Date(x1).getUTCFullYear(), step = yearStep(y1 - y0);
    for (let y = Math.ceil(y0 / step) * step; y <= y1; y += step) s += xGrid(f1(X(Date.UTC(y, 0, 1))), m.t, H - 4, PH - 8, y);
    s += el('text', { x: m.l, y: PH + 8, 'font-size': 10, fill: '#888' }, '下落（濃）→ 回復（淡）のタイムライン');

    ev.forEach((e) => {
      const a = X(Math.max(e.pk, x0)), b = X(Math.max(e.tr, x0)), c = X(e.rc || x1), cl = col(e);
      const cls = 'ch-band' + (st.sel == e.id ? ' sel' : ''), ly = PH + 14 + e._ln * (LH + 2);
      const band = (y, h, w, extra) => el('rect', { class: cls, 'data-id': e.id, x: f1(a), y, width: f1(Math.max(1.5, w)), height: h, fill: cl, ...extra });
      if (e.tr >= x0) {
        s += band(m.t, bot - m.t, b - a, { 'fill-opacity': e.bear ? 0.35 : 0.28 }); // 上段: 下落期間の帯
        s += band(ly, LH, b - a); // 下段: 下落（濃）
      }
      s += el('rect', { class: cls, 'data-id': e.id, x: f1(b), y: ly, width: f1(Math.max(1, c - b)), height: LH, fill: cl, 'fill-opacity': '.25',
        'stroke-dasharray': e.rc ? null : '2 2', stroke: e.rc ? null : cl }); // 下段: 回復（淡）
      if (st.sel == e.id) s += el('rect', { x: f1(a), y: m.t, width: f1(Math.max(1.5, c - a)), height: bot - m.t, fill: '#facc15', 'fill-opacity': '.18', stroke: '#ca8a04', 'pointer-events': 'none' });
    });
    s += el('path', { d: pathD(pts, X, Y), fill: 'none', stroke: 'var(--line)', 'stroke-width': 1.4, 'pointer-events': 'none' });

    box.innerHTML = svg(W, H, 'S&amp;P500と暴落期間', s);
    box.querySelector('svg').addEventListener('click', (ev) => {
      const r = ev.target.closest('.ch-band');
      if (r) pick(r.dataset.id, true);
    });
  }

  function info(e) {
    const box = $('.ch-info');
    if (!e) { box.innerHTML = INFO0; box.style.borderLeftColor = ''; return; }
    box.style.borderLeftColor = col(e);
    box.innerHTML = '<b>' + e.name + '</b> ' + tag(e, true) + (e.grp ? ' <span class="ch-lab">' + e.grp + '</span>' : '') + '<br>' +
      fdJa(e.pk, e.mon) + '（' + e.pv.toLocaleString() + '）→ 底 ' + fdJa(e.tr, e.mon) + '（' + e.tv.toLocaleString() + '）<b> ' + pct(e.dd) + '</b>／下落 ' +
      dur(e.fall) + '・回復 ' + (e.rc ? dur(e.rec) + '（' + fdJa(e.rc, e.mon) + '）' : ongo);
  }

  // 比較タブへ送るボタン。日次データのある1928年以降の暴落だけ（比較ツールの対象）
  function act(e) {
    const box = $('.ch-act');
    if (!onCompare || !e || e.mon) { box.innerHTML = ''; return; }
    box.innerHTML = '<button type="button" class="ch-tocmp">この暴落を「重ねて比較」で見る →</button>';
    box.firstChild.addEventListener('click', () => onCompare(e.id));
  }

  // 帯・行のタップ。表の行をもう一度タップすると解除
  function pick(id, fromChart) {
    st.sel = st.sel == id && !fromChart ? null : id;
    const e = EV.filter((x) => x.id == st.sel)[0];
    info(e);
    act(e);
    chart();
    R.querySelectorAll('tbody tr').forEach((tr) => {
      const on = tr.dataset.id == st.sel;
      tr.classList.toggle('sel', on);
      if (on && fromChart) $('.ch-wrap').scrollTop = tr.offsetTop - 40;
    });
  }

  function table() {
    const k = st.sort, dir = st.dir, v = vis().filter((e) => !st.q || e.name.indexOf(st.q) >= 0 || e.grp.indexOf(st.q) >= 0);
    v.sort((a, b) => {
      let x = a[k], y = b[k];
      if (k == 'name') return dir * x.localeCompare(y, 'ja');
      if (x == null) x = Infinity;
      if (y == null) y = Infinity;
      return dir * (x - y);
    });
    R.querySelectorAll('th').forEach((th) => { th.className = th.dataset.s == k ? (dir > 0 ? 'asc' : 'desc') : ''; });
    const td = (x) => '<td>' + x + '</td>';
    $('tbody').innerHTML = v.map((e) => '<tr data-id="' + e.id + '"' + (st.sel == e.id ? ' class="sel"' : '') + '>' +
      td(e.name + ' ' + tag(e)) + td('<b>' + pct(e.dd) + '</b>') + td(fdJa(e.pk, e.mon)) + td(fdJa(e.tr, e.mon)) +
      td(dur(e.fall)) + td(dur(e.rec)) + td(dur(e.tot)) + td(e.rc ? fdJa(e.rc, e.mon) : ongo) + '</tr>').join('') ||
      '<tr><td colspan="8">該当なし</td></tr>';
    R.querySelectorAll('tbody tr[data-id]').forEach((tr) => tr.addEventListener('click', () => pick(tr.dataset.id, false)));
  }
  return { refresh: () => { if (EV.length) chart(); } };
}
