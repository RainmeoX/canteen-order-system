/* ============================================================
   暖食食堂 · 组件：底部购物车栏
   挂载：window.Canteen.components.cartBar.update(el, count, total)
   结算按钮（#checkoutBtn）的点击由 app.js 统一委托处理
   ============================================================ */
window.Canteen = window.Canteen || {};
window.Canteen.components = window.Canteen.components || {};
(function () {
  function update(el, count, total) {
    if (count <= 0) { el.hidden = true; return; }
    el.hidden = false;
    el.innerHTML =
      '<div class="cartbar__info">' +
        '<span class="cartbar__count">' + count + '</span>' +
        '<span class="cartbar__label">已选</span>' +
        '<span class="cartbar__total">¥' + total.toFixed(2) + '</span>' +
      '</div>' +
      '<button class="btn btn--solid" id="checkoutBtn" type="button">去结算</button>';
  }
  window.Canteen.components.cartBar = { update };
})();
