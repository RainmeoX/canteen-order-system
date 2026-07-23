/* ============================================================
   暖食食堂 · 组件：Modal 弹窗
   挂载：window.Canteen.modal.open(title, bodyNode) / .close()
   ============================================================ */
window.Canteen = window.Canteen || {};
Canteen.modal = (function () {
  let root;
  function open(title, bodyNode) {
    if (!root) {
      root = document.createElement('div');
      root.className = 'modal';
      root.hidden = true;
      root.innerHTML = '<div class="modal__mask" data-close></div><div class="modal__panel" role="dialog" aria-modal="true"></div>';
      root.addEventListener('click', (e) => {
        if (e.target.dataset.close !== undefined || (e.target.classList && e.target.classList.contains('modal__x'))) close();
      });
      document.body.appendChild(root);
    }
    const panel = root.querySelector('.modal__panel');
    panel.innerHTML = '';
    const x = document.createElement('button');
    x.className = 'modal__x'; x.setAttribute('aria-label', '关闭'); x.textContent = '×';
    x.addEventListener('click', close);
    const h = document.createElement('h2');
    h.className = 'modal__title'; h.textContent = title;
    panel.appendChild(x); panel.appendChild(h); panel.appendChild(bodyNode);
    root.hidden = false;
  }
  function close() { if (root) root.hidden = true; }
  return { open, close };
})();
