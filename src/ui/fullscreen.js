// 全画面表示ボタン
// - Fullscreen API がある端末（Android・PC）は本物の全画面。Android は横向き固定も試す
// - ない端末（iPhone の Safari）は画面いっぱいの重ね表示（.ct-full の position:fixed）で代わりにする
// - 縦向きのスマホには「横向きにすると大きく見られます」を出す（CSS の orientation で切り替え）

const ON = '⛶ 全画面', OFF = '✕ 閉じる';

function reqFs(el) {
  const f = el.requestFullscreen || el.webkitRequestFullscreen;
  if (!f) return Promise.reject(new Error('no fullscreen'));
  try { return Promise.resolve(f.call(el, { navigationUI: 'hide' })); } catch (e) { return Promise.reject(e); }
}
const fsEl = () => document.fullscreenElement || document.webkitFullscreenElement || null;
function exitFs() {
  const f = document.exitFullscreen || document.webkitExitFullscreen;
  if (f && fsEl()) try { const p = f.call(document); if (p && p.catch) p.catch(() => {}); } catch (e) { /* 何もしない */ }
}

// target を全画面にするボタンを target の先頭に置く。onChange(全画面か) で描き直す
export function addFullscreen(target, onChange) {
  target.classList.add('ct-figwrap');
  target.insertAdjacentHTML('afterbegin', '<div class="ct-fsbar"><span class="ct-fshint">スマホを横向きにすると大きく見られます</span>' +
    '<button type="button" class="ct-fs" aria-label="全画面表示">' + ON + '</button></div>');
  const btn = target.querySelector('.ct-fs');
  let active = false;

  function set(on) {
    if (on == active) return;
    active = on;
    target.classList.toggle('ct-full', on);
    document.documentElement.classList.toggle('ct-noscroll', on);
    btn.textContent = on ? OFF : ON;
    btn.setAttribute('aria-label', on ? '全画面を閉じる' : '全画面表示');
    requestAnimationFrame(() => onChange(on));
  }
  function enter() {
    set(true);
    reqFs(target).then(() => {
      const o = screen.orientation;
      if (o && o.lock) o.lock('landscape').catch(() => {}); // 対応端末だけ（iPhone は不可）
    }).catch(() => {}); // 使えなければ重ね表示のまま
  }
  function exit() {
    const o = screen.orientation;
    if (o && o.unlock) try { o.unlock(); } catch (e) { /* 何もしない */ }
    exitFs();
    set(false);
  }
  btn.addEventListener('click', () => (active ? exit() : enter()));
  // 戻るボタン・Esc で全画面が解除されたとき
  ['fullscreenchange', 'webkitfullscreenchange'].forEach((n) => document.addEventListener(n, () => { if (active && !fsEl()) exit(); }));
  document.addEventListener('keydown', (e) => { if (active && e.key === 'Escape') exit(); });
  return { isFull: () => active };
}

// 全画面中のグラフの高さ: 画面の高さから、同じ枠の余白と、枠の中のほかの要素の高さ（上下マージン込み）を引いた残り。
// 一覧の詳細枠は、帯をタップすると2行になるので、全画面中は最初から2行分の高さを取っておく（styles.css の .ct-full .ch-info）
export function fitHeight(target, box, min) {
  const px = (v) => parseFloat(v) || 0;
  const ts = getComputedStyle(target);
  const others = Array.from(target.children).filter((c) => c !== box && !c.contains(box))
    .reduce((s, c) => { const cs = getComputedStyle(c); return s + c.getBoundingClientRect().height + px(cs.marginTop) + px(cs.marginBottom); }, 0);
  const bs = getComputedStyle(box);
  return Math.max(min, Math.floor(window.innerHeight - px(ts.paddingTop) - px(ts.paddingBottom) - px(bs.marginTop) - px(bs.marginBottom) - others - 6));
}
