// セグメント（ボタン群）とチップ

// items = [[値, ラベル], ...]
export function segHTML(cls, key, items, on) {
  return '<span class="' + cls + '"' + (key ? ' data-k="' + key + '"' : '') + '>' +
    items.map(([v, l]) => '<button data-v="' + v + '"' + (v == on ? ' class="on"' : '') + '>' + l + '</button>').join('') +
    '</span>';
}

// クリックされたボタンに .on を付け替えて onPick(値, ボタン)
export function bindSeg(seg, onPick) {
  seg.addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (!b) return;
    seg.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
    onPick(b.dataset.v, b);
  });
}

export function chipHTML(color, label, id) {
  return '<span class="chip"><i style="background:' + color + '"></i>' + label +
    '<button type="button" aria-label="外す" data-id="' + id + '">×</button></span>';
}
