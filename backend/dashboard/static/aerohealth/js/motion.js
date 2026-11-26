/* Count-up numbers and button ripples. Works on content the pages add after load. */
(function () {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  function countUp(el) {
    if (el.dataset.counted || el.children.length) return;
    const m = el.textContent.trim().match(/^(-?\d+(?:\.\d+)?)(.*)$/);
    if (!m) return;
    el.dataset.counted = '1';
    const end = parseFloat(m[1]), dec = (m[1].split('.')[1] || '').length, suffix = m[2], t0 = performance.now();
    (function step(t) {
      const p = Math.min((t - t0) / 900, 1), e = 1 - Math.pow(1 - p, 3);
      el.textContent = (end * e).toFixed(dec) + suffix;
      if (p < 1) requestAnimationFrame(step);
    })(t0);
  }
  const scan = root => root.querySelectorAll && root.querySelectorAll('.big').forEach(countUp);

  new MutationObserver(list => list.forEach(r => r.addedNodes.forEach(n => {
    if (n.nodeType !== 1) return;
    if (n.matches('.big')) countUp(n); else scan(n);
  }))).observe(document.body, { childList: true, subtree: true });
  scan(document);

  document.addEventListener('click', e => {
    const b = e.target.closest('.save,.livebtn,.ghost');
    if (!b) return;
    const r = b.getBoundingClientRect(), d = Math.max(r.width, r.height), s = document.createElement('span');
    s.className = 'rip';
    s.style.cssText = `width:${d}px;height:${d}px;left:${e.clientX - r.left - d / 2}px;top:${e.clientY - r.top - d / 2}px`;
    b.appendChild(s);
    setTimeout(() => s.remove(), 600);
  });
})();
