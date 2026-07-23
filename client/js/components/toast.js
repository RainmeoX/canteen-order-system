/* ============================================================
   暖食食堂 · 组件：Toast 轻提示
   挂载：window.Canteen.toast(msg, type, ms)
   ============================================================ */
window.Canteen = window.Canteen || {};
Canteen.toast = (function () {
  let wrap;
  function ensure() {
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'toast-wrap';
      document.body.appendChild(wrap);
    }
    return wrap;
  }
  function ico(type) { return type === 'ok' ? '✅' : type === 'err' ? '⚠️' : '🔔'; }
  return function (msg, type, ms) {
    const w = ensure();
    const el = document.createElement('div');
    el.className = 'toast' + (type === 'ok' ? ' toast--ok' : type === 'err' ? ' toast--err' : '');
    const i = document.createElement('span'); i.textContent = ico(type);
    const t = document.createElement('span'); t.textContent = msg;
    el.appendChild(i); el.appendChild(t);
    w.appendChild(el);
    setTimeout(() => {
      el.style.transition = 'opacity .3s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 320);
    }, ms || 2600);
  };
})();
