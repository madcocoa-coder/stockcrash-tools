// 比較ビュー: ピークからの騰落率を重ね合わせ＋表＋冒頭の自動文＋「今回に近い下落を探す」
import { DAY, fdSlash, dur, spct, year } from '../core/format.js';
import { loadEvents, shortName } from '../core/events.js';
import { SERIES, loadSeries } from '../series/registry.js';
import { segHTML, bindSeg, chipHTML } from '../ui/controls.js';
import { el, f1, svg, pathD, yGrid, xGrid, steps, onResize } from '../ui/chart.js';

export const COLORS = ['#b0352b', '#233b5e', '#1a8c80', '#b28430', '#6b4fa0', '#8a94a0'];
const MAXSEL = 6, SPAN = 1100; // 1件あたり読む日数（3年＋α）
const RANGES = [['90', '3か月'], ['180', '半年'], ['365', '1年'], ['730', '2年'], ['1095', '3年']];
const DEF_RE = [/リーマン/, /コロナ/, /2022年/, /ブラックマンデー/];
const READ0 = 'グラフをタップ（なぞる）と、その日数時点の下落率を表示';
const ERR = 'データを読み込めませんでした。時間をおいて再読み込みしてください。';

const HTML =
  '<div class="c-lead">データを読み込み中…</div>' +
  '<div class="c-row"><span class="c-lab">比べる暴落</span><span class="c-chips"></span></div>' +
  '<div class="c-row"><select class="c-add"><option value="">＋ 暴落を追加</option></select>' +
  '<button class="btn c-sim" type="button">今回に近い下落を探す</button><button class="btn c-main" type="button">主な暴落に戻す</button></div>' +
  '<div class="c-row"><span class="c-lab">表示期間</span>' + segHTML('seg c-range', null, RANGES, '365') + '</div>' +
  '<div class="c-fig"><div class="c-msg">データを読み込み中…</div></div>' +
  '<div class="c-read c-lab">' + READ0 + '</div>' +
  '<div class="c-wrap"><table><thead><tr><th>暴落</th><th>ピーク</th><th>最大下落</th><th>底まで</th><th>高値回復まで</th><th class="c-dayh">—</th></tr></thead><tbody></tbody></table></div>' +
  '<div class="c-note">横軸はピーク（直前の最高値）からの経過日数（暦日）、縦軸はピーク終値からの騰落率。S&amp;P500の日次終値（配当含まず）。1928年以降の、高値から10%以上下げた局面が対象。データは毎週更新。</div>';

// 日次終値をピーク比の騰落率 [[ピークからの日数, 騰落率], ...] に
function path(rows, e) {
  let base = null;
  const o = [];
  rows.forEach((x) => {
    if (!x[0] || !(x[1] > 0)) return;
    if (base == null) base = x[1];
    o.push([(x[0] - e.pk) / DAY, x[1] / base - 1]);
  });
  return o;
}
const slice = (all, e) => path(all.filter((x) => x[0] >= e.pk && x[0] <= e.pk + SPAN * DAY), e);
// d 日目の値（その日以前で最後の値）
function at(p, d) {
  let v = null;
  for (let i = 0; i < p.length; i++) { if (p[i][0] > d) break; v = p[i][1]; }
  return v;
}

export function mountCompare(host, { sheet }) {
  host.innerHTML = '<div class="cmp-root">' + HTML + '</div>';
  const R = host.firstChild, $ = (s) => R.querySelector(s), daily = SERIES.sp500;
  let EV = [], BY = {}, SEL = [], range = 365, cur = null, ALL = null;
  const CACHE = {};

  loadEvents(sheet).then(init).catch(() => { $('.c-lead').textContent = ERR; });

  function init(all) {
    EV = all.filter((e) => !e.mon); // 日次データのある1928年以降だけ
    EV.forEach((e) => { BY[e.id] = e; });
    const sel = $('.c-add'), grp = { b: '弱気相場（-20%以上）', c: '調整（-10〜20%）' };
    sel.insertAdjacentHTML('beforeend', ['b', 'c'].map((g) => '<optgroup label="' + grp[g] + '">' +
      EV.filter((e) => (g == 'b') == e.bear).slice().reverse().map((e) => '<option value="' + e.id + '">' + e.name + '（' + spct(e.dd) + '）</option>').join('') +
      '</optgroup>').join(''));
    sel.addEventListener('change', () => { if (sel.value) add(sel.value); sel.value = ''; });
    $('.c-main').addEventListener('click', () => setSel(defaults()));
    $('.c-sim').addEventListener('click', similar);
    bindSeg($('.c-range'), (v) => { range = +v; if (cur != null) cur = Math.min(cur, range); draw(); });
    $('.c-chips').addEventListener('click', (ev) => {
      const b = ev.target.closest('button');
      if (b) { SEL = SEL.filter((x) => x != b.dataset.id); update(); }
    });
    onResize(draw);
    const hs = (location.hash.match(/cmp=([\w,]+)/) || [])[1], ids = hs ? hs.split(',').filter((i) => BY[i]) : [];
    setSel(ids.length ? ids : defaults());
  }

  // 既定: 継続中＋リーマン／コロナ／2022年／ブラックマンデー
  function defaults() {
    const o = [], on = EV.filter((e) => e.on)[0];
    if (on) o.push(on.id);
    DEF_RE.forEach((re) => { const e = EV.filter((x) => re.test(x.name))[0]; if (e) o.push(e.id); });
    return o.slice(0, MAXSEL);
  }
  function setSel(ids) { SEL = ids.slice(0, MAXSEL); cur = 'auto'; update(); }
  function add(id) {
    if (SEL.indexOf(id) >= 0) return;
    if (SEL.length >= MAXSEL) SEL.pop();
    SEL.push(id);
    update();
  }

  function update() {
    try { history.replaceState(null, '', '#cmp=' + SEL.join(',')); } catch (e) { /* 埋め込み先で使えなくても続ける */ }
    $('.c-chips').innerHTML = SEL.map((id, i) => { const e = BY[id]; return chipHTML(COLORS[i], shortName(e) + ' ' + year(e.pk), id); }).join('');
    Promise.all(SEL.map(load)).then(draw).catch(() => { $('.c-fig').innerHTML = '<div class="c-msg">' + ERR + '</div>'; });
  }

  // 1件ぶんの日次を期間で絞って取る（全件を読み込み済みならそこから切り出す）
  function load(id) {
    if (CACHE[id]) return Promise.resolve(CACHE[id]);
    const e = BY[id];
    if (ALL) return Promise.resolve((CACHE[id] = slice(ALL, e)));
    const to = e.on ? Date.now() + DAY : e.pk + SPAN * DAY;
    return loadSeries(sheet, daily, 'daily', [e.pk, to]).then((rows) => (CACHE[id] = path(rows, e)));
  }

  function lines() {
    return SEL.map((id, i) => ({ e: BY[id], c: COLORS[i], p: (CACHE[id] || []).filter((x) => x[0] <= range) }));
  }

  function draw() {
    const box = $('.c-fig'), W = Math.max(300, box.clientWidth - 8), mob = W < 560, H = mob ? 320 : 420;
    const m = { l: mob ? 40 : 48, r: mob ? 10 : 16, t: 12, b: 26 };
    if (cur === 'auto') { // 継続中の最新日に縦線を合わせる
      const L0 = SEL.map((id) => BY[id]).filter((e) => e.on)[0], lp = L0 ? CACHE[L0.id] || [] : [];
      cur = lp.length ? Math.min(Math.round(lp[lp.length - 1][0]), range) : null;
    }
    const L = lines();
    let lo = -0.05, hi = 0.05;
    L.forEach((l) => l.p.forEach((x) => { lo = Math.min(lo, x[1]); hi = Math.max(hi, x[1]); }));
    lo = Math.floor(lo * 20 - 0.5) / 20;
    hi = Math.min(Math.ceil(hi * 20 + 0.2) / 20, 0.4);
    const X = (d) => m.l + d / range * (W - m.l - m.r), Y = (v) => m.t + (hi - v) / (hi - lo) * (H - m.t - m.b);

    let s = '';
    const step = hi - lo > 0.6 ? 0.2 : hi - lo > 0.3 ? 0.1 : 0.05;
    steps(lo, hi, step).forEach((v) => {
      const z = Math.abs(v) < 1e-9;
      s += yGrid(f1(Y(v)), m.l, W - m.r, Math.round(v * 100) + '%', { stroke: z ? '#9aa1a9' : '#eceef1', width: z ? 1.2 : 1, pad: 5, fill: '#5f6873' });
    });
    const xs = range <= 180 ? 30 : range <= 365 ? 90 : range <= 730 ? 180 : 365;
    for (let d = 0; d <= range; d += xs) s += xGrid(f1(X(d)), m.t, H - m.b, H - 8, d ? d + '日' : 'ピーク', { stroke: '#f4f5f7', fill: '#5f6873' });

    L.slice().reverse().forEach((l) => { // 先頭（今回）を最後に描いて一番上に
      if (!l.p.length) return;
      s += el('path', { d: pathD(l.p, (d) => X(d), (v) => Y(Math.min(v, hi))), fill: 'none', stroke: l.c, 'stroke-width': l.e.on ? 3 : 2, 'stroke-linejoin': 'round', opacity: l.e.on ? 1 : 0.9 });
      const mn = l.p.reduce((a, x) => (x[1] < a[1] ? x : a));
      s += el('circle', { cx: f1(X(mn[0])), cy: f1(Y(mn[1])), r: 3.5, fill: l.c });
      if (l.e.on) { const z = l.p[l.p.length - 1]; s += el('circle', { cx: f1(X(z[0])), cy: f1(Y(z[1])), r: 5, fill: '#fff', stroke: l.c, 'stroke-width': 2.5 }); }
    });
    if (cur != null) {
      const cx = f1(X(cur));
      s += el('line', { x1: cx, x2: cx, y1: m.t, y2: H - m.b, stroke: '#14161a', 'stroke-dasharray': '3 3' }) +
        el('text', { x: cx, y: m.t + 10, dx: 4, 'font-size': 10, fill: '#14161a' }, Math.round(cur) + '日目');
    }
    s += el('rect', { class: 'hit', x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: 'transparent' });
    box.innerHTML = svg(W, H, '暴落の比較チャート', s);

    const sv = box.querySelector('svg');
    const mv = (ev) => {
      const r = sv.getBoundingClientRect();
      const px = ((ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left) * W / r.width, d = (px - m.l) / (W - m.l - m.r) * range;
      if (d < 0 || d > range) return;
      cur = Math.round(d);
      draw();
    };
    sv.addEventListener('click', mv);
    sv.addEventListener('mousemove', mv);
    sv.addEventListener('touchmove', mv, { passive: true });
    table(L);
    lead(L);
  }

  function table(L) {
    const d = cur == null ? null : Math.round(cur);
    $('.c-dayh').textContent = d == null ? '—' : d + '日目の騰落率';
    $('tbody').innerHTML = L.map((l) => {
      const e = l.e, full = CACHE[e.id] || [], v = d == null ? null : at(full, d), rc = e.rc ? Math.round((e.rc - e.pk) / DAY) : null;
      // 最大下落・底までは日次の「ピーク〜回復日」の最安値で（行の底値とは違うことがある）
      const mn = full.filter((x) => rc == null || x[0] <= rc).reduce((a, x) => (x[1] < a[1] ? x : a), [Math.round((e.tr - e.pk) / DAY), e.dd]);
      return '<tr><td><span class="chip" style="border:0;padding:0"><i style="background:' + l.c + '"></i></span> ' + e.name + '</td><td>' + fdSlash(e.pk) +
        '</td><td class="neg"><b>' + spct(mn[1]) + '</b></td><td>' + dur(Math.round(mn[0])) + '</td><td>' + (e.on ? '<span class="neg">未回復</span>' : dur(rc)) +
        '</td><td>' + (v == null ? '—' : '<b' + (v < 0 ? ' class="neg"' : '') + '>' + spct(v) + '</b>') + '</td></tr>';
    }).join('') || '<tr><td colspan="6">暴落を選んでください</td></tr>';
    $('.c-read').innerHTML = d == null ? READ0 : '<b>' + d + '日目</b>　' + L.map((l) => {
      const v = at(CACHE[l.e.id] || [], d);
      return '<span style="color:' + l.c + '">● ' + shortName(l.e) + ' ' + (v == null ? '—' : spct(v)) + '</span>';
    }).join('');
  }

  // 冒頭の自動文「今回はピークから○日で-x%（最大-y%）。同じ○日目の時点で、…でした。」
  function lead(L) {
    const box = $('.c-lead'), on = L.filter((l) => l.e.on)[0];
    if (!on) { box.textContent = '比べたい暴落を選ぶと、ピークからの下落の進み方を重ねて表示します。'; return; }
    const p = CACHE[on.e.id] || [];
    if (!p.length) return;
    const z = p[p.length - 1], d = Math.round(z[0]);
    const others = L.filter((l) => l !== on).map((l) => {
      const v = at(CACHE[l.e.id] || [], d);
      return v == null ? '' : shortName(l.e) + '（' + year(l.e.pk) + '年）は' + spct(v);
    }).filter(String);
    box.innerHTML = '今回はピークから' + d + '日で' + spct(z[1]) + '（最大' + spct(on.e.dd) + '）。' + (others.length ? '同じ' + d + '日目の時点で、' + others.join('、') + 'でした。' : '');
  }

  // 日次全件（約45万字）を押したときだけ読み、0〜N日を3日おきにRMSEで比べて近い4件
  function similar() {
    const on = EV.filter((e) => e.on)[0], btn = $('.c-sim');
    if (!on) { btn.textContent = '継続中の下落がありません'; return; }
    btn.textContent = '計算中…';
    const go = () => {
      const p = CACHE[on.id] || slice(ALL, on), N = Math.round(p[p.length - 1][0]), sc = [];
      EV.forEach((e) => {
        if (e.on) return;
        const q = slice(ALL, e);
        let s = 0, n = 0;
        for (let d = 0; d <= N; d += 3) {
          const a = at(p, d), b = at(q, d);
          if (a == null || b == null) continue;
          s += (a - b) * (a - b);
          n++;
        }
        if (n > 3) sc.push([e.id, Math.sqrt(s / n)]);
      });
      sc.sort((a, b) => a[1] - b[1]);
      btn.textContent = '今回に近い下落を探す';
      setSel([on.id].concat(sc.slice(0, 4).map((x) => x[0])));
    };
    if (ALL) { go(); return; }
    loadSeries(sheet, daily, 'daily').then((rows) => { ALL = rows; go(); }).catch(() => { btn.textContent = '読み込みに失敗しました'; });
  }
}
