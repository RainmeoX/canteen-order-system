/* ============================================================
   暖食食堂 · 应用编排（启动 / 路由 / 提醒引擎 / 结算）
   依赖（按 index.html 顺序加载）：api → store → toast/modal →
   components/* → views/* → app
   ============================================================ */
(function () {
  const { api, store, toast, modal } = window.Canteen;

  // ---------- DOM ----------
  const $ = (id) => document.getElementById(id);
  const entryEl = $('entry');
  const navEl = document.querySelector('.nav');
  const tabbarEl = document.querySelector('.tabbar');
  const cartbarEl = $('cartbar');
  const userChipName = $('userChipName');
  const reminderEl = $('reminder');

  // ---------- 提醒引擎状态 ----------
  const reminder = window.Canteen.components.createReminder(reminderEl);
  let latestOrders = [];
  let latestDeliveries = [];
  const fired = {};   // 通知去重：order_no+type

  // ---------- 视图上下文 ----------
  const ctx = {
    api, store, toast, modal,
    navigate,
    setSession,
    refreshCart,
    onTodayOrders(orders) { latestOrders = orders || []; pushReminder(); },
  };

  function pushReminder() { reminder.update(latestOrders, latestDeliveries); }
  function requestNotify() {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'default') { try { Notification.requestPermission(); } catch (e) {} }
  }
  function checkNotify(pickups) {
    pickups.forEach((p) => {
      const soonKey = p.order_no + ':soon';
      const nowKey = p.order_no + ':now';
      if (p.left <= 1800 && p.left > 0 && !fired[soonKey]) {
        fired[soonKey] = true;
        const msg = '取餐倒计时 30 分钟：' + p.pickup_code;
        if (Notification.permission === 'granted') new Notification('暖食食堂 · 记得去取餐', { body: msg });
        else toast(msg, 'ok');
      }
      if (p.left <= 0 && !fired[nowKey]) {
        fired[nowKey] = true;
        const msg = '取餐已到点：' + p.pickup_code + '，请尽快到食堂一楼自取';
        if (Notification.permission === 'granted') new Notification('暖食食堂 · 取餐时间到', { body: msg });
        else toast(msg, 'err');
      }
    });
  }

  // ---------- 路由 ----------
  const VIEWS = { menu: 'view-menu', orders: 'view-orders', health: 'view-health' };
  function navigate(view) {
    Object.keys(VIEWS).forEach((k) => { $(VIEWS[k]).hidden = (k !== view); });
    document.querySelectorAll('.tabbar__btn').forEach((b) => {
      const on = b.dataset.view === view;
      b.classList.toggle('is-active', on);
    });
    if (view === 'menu' && window.Canteen.views.menu) window.Canteen.views.menu.refresh();
    if (view === 'orders' && window.Canteen.views.orders) window.Canteen.views.orders.refresh();
    if (view === 'health' && window.Canteen.views.health) window.Canteen.views.health.refresh();
  }

  // ---------- 购物车 ----------
  function refreshCart() {
    const count = store.cartCount();
    const total = store.cartTotal();
    window.Canteen.components.cartBar.update(cartbarEl, count, total);
  }
  cartbarEl.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'checkoutBtn') checkout();
  });

  async function checkout() {
    const s = store.session;
    if (!s) { toast('请先进入', 'err'); return; }
    const items = Object.keys(store.cart).map((k) => store.cart[k]);
    if (!items.length) { toast('购物车是空的', 'err'); return; }
    const bed = s.mode === 'bed';
    const body = document.createElement('div');
    const listHtml = items.map((c) =>
      '<div class="order__item"><b>' + c.name + ' ×' + c.qty + '</b><span>¥' + (c.price * c.qty).toFixed(2) + '</span></div>'
    ).join('');
    body.innerHTML =
      '<div class="order__items">' + listHtml + '</div>' +
      '<div class="summary-line">履约方式：<b>' + (bed ? '床旁配送（送至床位）' : '食堂自取（一楼大厅）') + '</b></div>' +
      '<div class="form-row"><label>备注（忌口 / 口味）</label><input id="ckRemark" type="text" placeholder="如：不要辣"></div>';
    const ok = document.createElement('button');
    ok.className = 'btn btn--solid btn--block'; ok.type = 'button'; ok.textContent = '确认下单 ¥' + store.cartTotal().toFixed(2);
    ok.addEventListener('click', async () => {
      const hour = new Date().getHours();
      const meal = hour < 10 ? '早餐' : hour < 14 ? '午餐' : '晚餐';
      const remark = body.querySelector('#ckRemark').value.trim();
      ok.disabled = true; ok.textContent = '下单中…';
      const r = await api.placeOrder({
        user_id: s.user_id,
        items: items.map((c) => ({ dish_name: c.name, quantity: c.qty })),
        fulfillment_mode: bed ? 'bed_delivery' : 'pickup',
        patient_id: s.patient_id || null,
        ward_id: s.ward ? s.ward.id : null,
        meal_slot: meal,
        remark,
      });
      if (!r.success) { toast(r.message || '下单失败', 'err'); ok.disabled = false; ok.textContent = '确认下单'; return; }
      modal.close();
      store.clearCart(); refreshCart();
      requestNotify();
      const tip = bed
        ? '已下单，配送员将送达床位（' + (s.ward ? s.ward.dept + s.ward.bed_no : '') + '）'
        : '下单成功 · 取餐码 ' + (r.pickup_code || '—') + ' · 截止 ' + (r.take_time || '');
      toast(tip, 'ok', 3600);
      if (window.Canteen.views.orders) window.Canteen.views.orders.refresh();
      refreshReminderData();
    });
    body.appendChild(ok);
    modal.open('确认订单', body);
  }

  // ---------- 会话 ----------
  function setSession(s) {
    store.setSession(s);
    onSession();
  }
  function onSession() {
    const s = store.session;
    if (!s) {
      entryEl.hidden = false; navEl.style.display = 'none'; tabbarEl.style.display = 'none'; cartbarEl.hidden = true;
      window.Canteen.views.bed.mount(entryEl, ctx);
      return;
    }
    entryEl.hidden = true; navEl.style.display = ''; tabbarEl.style.display = '';
    userChipName.textContent = s.mode === 'bed'
      ? (s.ward ? s.ward.dept + ' ' + (s.ward.bed_no || '') : '床位') + (s.diet_type_label ? ' · ' + s.diet_type_label : '')
      : (s.user_id || '访客');
    // 挂载视图（仅首次）
    if (!viewsMounted) {
      window.Canteen.views.menu.mount(ctx);
      window.Canteen.views.orders.mount(ctx);
      window.Canteen.views.health.mount(ctx);
      viewsMounted = true;
    }
    navigate('menu');
    refreshCart();
    refreshReminderData();
  }

  function openUserMenu() {
    const s = store.session;
    if (!s) return;
    const body = document.createElement('div');
    const info = s.mode === 'bed'
      ? '床头码：<b>' + s.bed_qr_token + '</b><br>患者：<b>' + (s.patient ? s.patient.name : (s.patient_id || '')) + '</b><br>饮食医嘱：<b>' + (s.diet_type_label || '—') + '</b><br>' + (s.constraints || '')
      : '身份：<b>' + s.user_id + '</b>（食堂自取）';
    body.innerHTML = '<div class="summary-line">' + info + '</div>';
    const sw = document.createElement('button');
    sw.className = 'btn btn--ghost btn--block'; sw.type = 'button'; sw.textContent = '切换身份 / 换床位';
    sw.addEventListener('click', () => { modal.close(); store.clearSession(); onSession(); });
    body.appendChild(sw);
    modal.open('当前身份', body);
  }

  // ---------- 提醒数据刷新 ----------
  async function refreshReminderData() {
    const s = store.session;
    if (!s) return;
    const [o, d] = await Promise.all([
      api.orders(s.user_id, 'today'),
      api.deliveries(''),
    ]);
    if (o.success) { latestOrders = o.data || []; if (window.Canteen.views.orders) window.Canteen.views.orders.refresh(); }
    if (d.success) latestDeliveries = d.deliveries || [];
    pushReminder();
  }

  // ---------- 启动 ----------
  let viewsMounted = false;
  document.querySelector('.tabbar').addEventListener('click', (e) => {
    const b = e.target.closest('.tabbar__btn'); if (b) navigate(b.dataset.view);
  });
  $('userChip').addEventListener('click', openUserMenu);

  // 每秒刷新倒计时；每 20 秒重新拉取订单/配送
  setInterval(() => { const p = reminder.tick(); if (p) checkNotify(p); }, 1000);
  setInterval(() => { if (store.session) refreshReminderData(); }, 20000);

  onSession();
})();
