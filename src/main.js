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

function boot() {
  injectCss();
  document.querySelectorAll('[data-tool="crash"]').forEach((host) => {
    if (host.dataset.ready) return; // 2回読み込まれても二重に描かない
    host.dataset.ready = '1';
    const mount = VIEWS[host.dataset.tab] || mountList;
    mount(host, { sheet: host.dataset.sheet || DEFAULT_SHEET });
  });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
else boot();

window.CrashTools = { boot, version: __VERSION__ };
