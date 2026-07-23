/* ============================================================
   暖食食堂 · 组件：订单卡（含履约模式 / 配送状态）
   挂载：window.Canteen.components.orderCard(order)
   order 来自 GET /api/v1/orders：
     order_no, order_time, take_deadline, status, pickup_code,
     fulfillment_mode('pickup'|'bed_delivery'), meal_slot,
     delivery_status('ready'|'dispatching'|'delivered'), items[], total_price
   ============================================================ */
window.Canteen = window.Canteen || {};
window.Canteen.components = window.Canteen.components || {};
(function () {
  const STATUS = {
    pending:  { label: '待取 / 待配送', cls: 'pending' },
    taken:    { label: '已取餐', cls: 'taken' },
    cancelled: { label: '已取消', cls: 'cancelled' },
    overtime:  { label: '已超时', cls: 'overtime' },
  };
  const DELIV = {
    ready:        { label: '备餐中 · 稍后送达', cls: 'ready' },
    dispatching:  { label: '配送员已出发', cls: 'dispatching' },
    delivered:    { label: '已送达床位', cls: 'delivered' },
  };

  function orderCard(o) {
    const st = STATUS[o.status] || STATUS.pending;
    const bed = o.fulfillment_mode === 'bed_delivery';

    const el = document.createElement('article');
    el.className = 'order';

    const head = document.createElement('div');
    head.className = 'order__head';
    const no = document.createElement('span');
    no.className = 'order__no'; no.textContent = o.order_no;
    const badges = document.createElement('div');
    badges.style.display = 'flex'; badges.style.gap = '6px'; badges.style.flexWrap = 'wrap';
    const mode = document.createElement('span');
    mode.className = 'order__mode' + (bed ? '' : ' order__mode--pickup');
    mode.textContent = bed ? '床旁配送' : '食堂自取';
    const stEl = document.createElement('span');
    stEl.className = 'order__status order__status--' + st.cls;
    stEl.textContent = st.label;
    badges.appendChild(mode); badges.appendChild(stEl);
    head.appendChild(no); head.appendChild(badges);

    const items = document.createElement('div');
    items.className = 'order__items';
    (o.items || []).forEach((it) => {
      const row = document.createElement('div');
      row.className = 'order__item';
      const b = document.createElement('b'); b.textContent = it.dish_name + ' ×' + it.quantity;
      const s = document.createElement('span');
      s.textContent = '¥' + (Number(it.subtotal) || 0).toFixed(2);
      row.appendChild(b); row.appendChild(s);
      items.appendChild(row);
    });

    const foot = document.createElement('div');
    foot.className = 'order__foot';
    const left = document.createElement('span');
    const code = document.createElement('b');
    code.className = 'order__code'; code.textContent = o.pickup_code || '—';
    left.innerHTML = '取餐码 ';
    left.appendChild(code);
    const time = document.createElement('span');
    time.textContent = ' · 截止 ' + (o.take_deadline ? o.take_deadline.slice(11) : '—');
    left.appendChild(time);
    const total = document.createElement('span');
    total.className = 'order__total';
    total.textContent = '¥' + (Number(o.total_price) || 0).toFixed(2);
    foot.appendChild(left); foot.appendChild(total);

    el.appendChild(head); el.appendChild(items); el.appendChild(foot);

    // 配送进度
    if (bed && o.delivery_status) {
      const dv = DELIV[o.delivery_status] || DELIV.ready;
      const d = document.createElement('div');
      d.className = 'order__delivery order__delivery--' + dv.cls;
      d.style.marginTop = '10px';
      d.textContent = '配送状态：' + dv.label;
      el.appendChild(d);
    }
    return el;
  }

  window.Canteen.components.orderCard = orderCard;
})();
