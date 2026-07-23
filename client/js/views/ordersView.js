/* ============================================================
   暖食食堂 · 视图：我的订单（今日 + 历史查询，含履约/配送状态）
   挂载：window.Canteen.views.orders.{mount(ctx), refresh()}
   今日加载后通过 ctx.onTodayOrders(orders) 通知 app 更新提醒
   ============================================================ */
window.Canteen = window.Canteen || {};
window.Canteen.views = window.Canteen.views || {};
(function () {
  let ctx;
  let range = 'today';

  function renderList(box, data) {
    box.innerHTML = '';
    const list = (data && data.data) || [];
    if (!list.length) {
      box.innerHTML = '<div class="empty"><span class="empty__emoji">📭</span>还没有订单</div>';
      return;
    }
    list.forEach((o) => box.appendChild(window.Canteen.components.orderCard(o)));
  }

  async function loadToday() {
    const s = ctx.store.session;
    if (!s) return;
    const r = await ctx.api.orders(s.user_id, 'today');
    renderList(document.getElementById('ordersTodayList'), r);
    if (r.success && ctx.onTodayOrders) ctx.onTodayOrders(r.data || []);
  }

  async function loadHistory(start, end) {
    const s = ctx.store.session;
    if (!s) return;
    const r = await ctx.api.orders(s.user_id, 'history', { start, end });
    renderList(document.getElementById('ordersHistoryList'), r);
    if (!r.success) ctx.toast(r.message || '查询失败', 'err');
  }

  function bindSeg() {
    const btns = document.querySelectorAll('#view-orders .seg__btn');
    btns.forEach((b) => {
      b.addEventListener('click', () => {
        range = b.dataset.range;
        btns.forEach((x) => {
          const on = x === b;
          x.classList.toggle('is-active', on);
          x.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        document.getElementById('ordersToday').hidden = range !== 'today';
        document.getElementById('ordersHistory').hidden = range !== 'history';
        if (range === 'history') {
          const f = document.getElementById('historyForm');
          loadHistory(f.histStart.value, f.histEnd.value);
        }
      });
    });
    const form = document.getElementById('historyForm');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      loadHistory(form.histStart.value, form.histEnd.value);
    });
  }

  function mount(c) {
    ctx = c;
    bindSeg();
    loadToday();
  }
  function refresh() { if (range === 'today') loadToday(); else loadHistory(ctx.store.session ? null : null); }
  // 历史面板也需要能手动刷新
  function refreshHistory() {
    const f = document.getElementById('historyForm');
    if (f) loadHistory(f.histStart.value, f.histEnd.value);
  }

  window.Canteen.views.orders = { mount, refresh, refreshHistory };
})();
