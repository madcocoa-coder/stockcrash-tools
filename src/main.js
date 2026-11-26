// エントリ: ページ内の [data-tool="crash"] を初期化する
// 埋め込み: <div data-tool="crash" data-tab="list|compare" data-sheet="<シートID>"></div>
import css from './styles.css';
import { DEFAULT_SHEET } from './core/data.js';
import { mountList } from './views/list.js';
import { mountCompare } from './views/compare.js';

const VIEWS = { list: mountList, compare: mountCompare };

function injectCss() {
  if (document.getElementById('crash-tools-css')) return;
  const s = document.createElement('style');
  s.id = 'crash-tools-css';
  s.textContent = css;
  document.head.appendChild(s);
}

const TABS = [['list', '暴落の一覧'], ['compare', '重ねて比較']];

// 1つの埋め込みに「一覧」「比較」の2タブを載せる。data-tab は最初に開くタブ。
// 2つ目のタブは初めて開いたときに読み込む（一覧ページで比較用の日次データを読まないため）
function mountTabs(host, sheet) {
  host.innerHTML = '<div class="ct-tabs" role="tablist">' +
    TABS.map(([k, l]) => '<button type="button" role="tab" data-t="' + k + '">' + l + '</button>').join('') + '</div>' +
    TABS.map(([k]) => '<div class="ct-pane" data-p="' + k + '" hidden></div>').join('');
  const api = {};
  const pane = (k) => host.querySelector('.ct-pane[data-p="' + k + '"]');
  function show(k) {
    host.querySelectorAll('.ct-tabs button').forEach((b) => { const on = b.dataset.t == k; b.classList.toggle('on', on); b.setAttribute('aria-selected', on); });
    TABS.forEach(([t]) => { pane(t).hidden = t != k; });
    if (!api[k]) api[k] = VIEWS[k](pane(k), { sheet, onCompare: k == 'list' ? toCompare : null });
    else api[k].refresh(); // 隠れている間に幅が変わっていても描き直す
  }
  function toCompare(id) {
    show('compare');
    api.compare.add(id);
    const top = host.getBoundingClientRect().top;
    if (top < 0) host.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  host.querySelector('.ct-tabs').addEventListener('click', (ev) => { const b = ev.target.closest('button'); if (b) show(b.dataset.t); });
  // 比較の共有URL（#cmp=…）で来たら比較タブから開く
  show(/(^|[#&])cmp=/.test(location.hash) ? 'compare' : VIEWS[host.dataset.tab] ? host.dataset.tab : 'list');
}

function boot() {
  injectCss();
  document.querySelectorAll('[data-tool="crash"]').forEach((host) => {
    if (host.dataset.ready) return; // 2回読み込まれても二重に描かない
    host.dataset.ready = '1';
    mountTabs(host, host.dataset.sheet || DEFAULT_SHEET);
  });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
else boot();

window.CrashTools = { boot, version: __VERSION__ };
