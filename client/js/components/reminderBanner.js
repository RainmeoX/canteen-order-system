/* ============================================================
   暖食食堂 · 组件：智能取餐 / 配送提醒横幅
   挂载：window.Canteen.components.createReminder(el)
   返回 { update(orders, deliveries), tick() }
   - update() 仅重建列表（带 data-deadline 的倒计时节点）
   - tick()   每秒刷新倒计时文本，避免重绘闪烁
   ============================================================ */
window.Canteen = window.Canteen || {};
window.Canteen.components = window.Canteen.components || {};
(function () {
  function parseTime(str) {
    if (!str) return null;
    const d = new Date(String(str).replace(' ', 'T'));
    return isNaN(d.getTime()) ? null : d;
  }
  function fmt(left) {
    if (left <= 0) return '已过点';
    const s = Math.floor(left);
    if (s >= 3600) { const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return h + '小时' + m + '分'; }
    const m = Math.floor(s / 60), ss = s % 60;
    return m + ':' + String(ss).padStart(2, '0');
  }
  const DELIV = {
    ready: '备餐中 · 稍后送达',
    dispatching: '配送员已出发',
    delivered: '已送达床位',
  };

  function createReminder(el) {
    const title = el.querySelector('#reminderTitle');
    const text = el.querySelector('#reminderText');
    const list = el.querySelector('#reminderList');
    let data = { orders: [], deliveries: [] };

    function build() {
      const pending = (data.orders || []).filter((o) => o.status === 'pending');
      const items = [];
      pending.forEach((o) => {
        const bed = o.fulfillment_mode === 'bed_delivery';
        const item = document.createElement('div');
        item.className = 'reminder__item';
        const code = document.createElement('span');
        code.className = 'reminder__code';
        code.textContent = o.pickup_code || '—';
        const right = document.createElement('span');
        if (bed) {
          const d = (data.deliveries || []).find((x) => x.order_no === o.order_no);
          const st = d ? d.status : 'ready';
          right.className = 'reminder__mode';
          right.textContent = (o.meal_slot ? o.meal_slot + ' · ' : '') + (DELIV[st] || DELIV.ready);
        } else {
          const dl = parseTime(o.take_deadline);
          const left = dl ? Math.floor((dl.getTime() - Date.now()) / 1000) : 0;
          right.className = 'reminder__cd' + (left <= 1800 && left > 0 ? ' is-soon' : '');
          right.dataset.deadline = dl ? dl.getTime() : '';
          right.textContent = '自取 · ' + fmt(left);
        }
        item.appendChild(code); item.appendChild(right);
        items.push(item);
      });
      if (!items.length) { el.hidden = true; list.innerHTML = ''; return; }
      el.hidden = false;
      const bedCount = pending.filter((o) => o.fulfillment_mode === 'bed_delivery').length;
      title.textContent = bedCount ? '床旁配送进行中' : '记得及时去取餐';
      text.textContent = '你有 ' + pending.length + ' 笔待取 / 待送达订单。';
      list.innerHTML = '';
      items.forEach((it) => list.appendChild(it));
    }

    function tick() {
      if (el.hidden) return;
      list.querySelectorAll('.reminder__cd').forEach((sp) => {
        const dl = Number(sp.dataset.deadline) || 0;
        const left = Math.floor((dl - Date.now()) / 1000);
        sp.textContent = '自取 · ' + fmt(left);
        sp.classList.toggle('is-soon', left <= 1800 && left > 0);
      });
      // 返回待提醒的取餐订单（供 app.js 触发系统通知）
      return (data.orders || [])
        .filter((o) => o.status === 'pending' && o.fulfillment_mode !== 'bed_delivery')
        .map((o) => {
          const dl = parseTime(o.take_deadline);
          return { order_no: o.order_no, pickup_code: o.pickup_code, left: dl ? Math.floor((dl.getTime() - Date.now()) / 1000) : 0 };
        });
    }

    return {
      update(orders, deliveries) { data = { orders: orders || [], deliveries: deliveries || [] }; build(); },
      tick,
    };
  }

  window.Canteen.components.createReminder = createReminder;
})();
