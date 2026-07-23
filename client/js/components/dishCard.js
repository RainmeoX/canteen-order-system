/* ============================================================
   暖食食堂 · 组件：菜品卡（含医嘱推荐/禁忌标记、库存、步进器）
   挂载：window.Canteen.components.dishCard(dish, handlers)
   dish 字段兼容两种来源：
     · 床头码菜单：recommended(bool) / diet_locked(bool) / nutrition_info(Object)
     · 通用菜单：nutrition_info(String) / allergy_tag / alias
   ============================================================ */
window.Canteen = window.Canteen || {};
window.Canteen.components = window.Canteen.components || {};
(function () {
  function parseNutri(d) {
    if (!d) return {};
    if (typeof d.nutrition_info === 'object' && d.nutrition_info) return d.nutrition_info;
    if (typeof d.nutrition_info === 'string' && d.nutrition_info) {
      try { return JSON.parse(d.nutrition_info) || {}; } catch (e) { return {}; }
    }
    return {};
  }

  function tag(text, cls) {
    const s = document.createElement('span');
    s.className = 'tag' + (cls ? ' ' + cls : '');
    s.textContent = text;
    return s;
  }

  function dishCard(dish, h) {
    const nutri = parseNutri(dish);
    const recommended = !!dish.recommended;
    const remaining = dish.remaining == null ? 0 : dish.remaining;
    const limit = dish.limit_per_person == null ? 99 : dish.limit_per_person;
    const out = remaining <= 0;
    const sugar = Number(nutri.sugar) || 0;

    const el = document.createElement('article');
    el.className = 'dish' + (out ? ' is-out' : '');

    const thumb = document.createElement('div');
    thumb.className = 'dish__thumb';
    thumb.textContent = dish.image_emoji || '🍽️';

    const main = document.createElement('div');
    main.className = 'dish__main';

    const top = document.createElement('div');
    top.className = 'dish__top';
    const name = document.createElement('h3');
    name.className = 'dish__name'; name.textContent = dish.name;
    const price = document.createElement('div');
    price.className = 'dish__price';
    price.textContent = '¥' + (Number(dish.price) || 0).toFixed(2);
    top.appendChild(name); top.appendChild(price);

    const meta = document.createElement('div');
    meta.className = 'dish__meta';
    if (recommended) meta.appendChild(tag('推荐', 'tag--sage'));
    if (dish.allergy_tag) meta.appendChild(tag(dish.allergy_tag, 'tag--allergy'));
    if (sugar >= 15) meta.appendChild(tag('含添加糖', 'tag--sugar'));
    if (dish.category) meta.appendChild(tag(dish.category));

    const desc = document.createElement('p');
    desc.className = 'dish__desc';
    desc.textContent = dish.description || (nutri.note || '');

    const foot = document.createElement('div');
    foot.className = 'dish__foot';

    const stock = document.createElement('span');
    if (out) { stock.className = 'dish__stock is-out'; stock.textContent = '已售罄'; }
    else if (remaining <= 5) { stock.className = 'dish__stock is-low'; stock.textContent = '仅剩 ' + remaining + ' 份'; }
    else { stock.className = 'dish__stock'; stock.textContent = '余 ' + remaining + ' 份'; }

    // 步进器
    const stepper = document.createElement('div');
    stepper.className = 'stepper';
    const minus = document.createElement('button');
    minus.className = 'stepper__btn'; minus.type = 'button'; minus.textContent = '−'; minus.setAttribute('aria-label', '减少');
    const n = document.createElement('span');
    n.className = 'stepper__n'; n.textContent = h.cartQty(dish.name);
    const plus = document.createElement('button');
    plus.className = 'stepper__btn'; plus.type = 'button'; plus.textContent = '+'; plus.setAttribute('aria-label', '增加');
    minus.disabled = h.cartQty(dish.name) <= 0;
    plus.disabled = out || h.cartQty(dish.name) >= remaining || h.cartQty(dish.name) >= limit;
    minus.addEventListener('click', () => h.onSet(dish.name, h.cartQty(dish.name) - 1));
    plus.addEventListener('click', () => h.onAdd(dish.name, dish.price));

    stepper.appendChild(minus); stepper.appendChild(n); stepper.appendChild(plus);
    foot.appendChild(stock); foot.appendChild(stepper);

    main.appendChild(top); main.appendChild(meta);
    if (desc.textContent) main.appendChild(desc);
    main.appendChild(foot);

    el.appendChild(thumb); el.appendChild(main);
    return el;
  }

  window.Canteen.components.dishCard = dishCard;
})();
