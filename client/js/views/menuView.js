/* ============================================================
   暖食食堂 · 视图：今日点餐（床头码过滤菜单 / 通用菜单 + 购物车）
   挂载：window.Canteen.views.menu.{mount(ctx), refresh()}
   ============================================================ */
window.Canteen = window.Canteen || {};
window.Canteen.views = window.Canteen.views || {};
(function () {
  let menu = [];      // 当前菜品
  let cats = ['全部'];
  let activeCat = '全部';
  let kw = '';
  let ctx;

  function normalize(list, bed) {
    return (list || []).map((d) => ({
      name: d.name, category: d.category, price: d.price,
      remaining: d.remaining, limit_per_person: d.limit_per_person,
      description: d.description, image_emoji: d.image_emoji,
      allergy_tag: d.allergy_tag, nutrition_info: d.nutrition_info,
      recommended: bed ? !!d.recommended : false,
    }));
  }

  async function loadMenu() {
    const s = ctx.store.session;
    let list = null;
    if (s && s.mode === 'bed') {
      const r = await ctx.api.bedEnter(s.bed_qr_token);
      if (r.success) list = normalize(r.menu, true);
    } else {
      const r = await ctx.api.menu();
      if (r.success) list = normalize(r.data, false);
    }
    if (!list) { ctx.toast('菜单加载失败', 'err'); return; }
    menu = list;
    const set = new Set(['全部']);
    menu.forEach((d) => { if (d.category) set.add(d.category); });
    cats = Array.from(set);
    renderCats();
    renderGrid();
  }

  function renderCats() {
    const box = document.getElementById('catTabs');
    box.innerHTML = '';
    cats.forEach((c) => {
      const b = document.createElement('button');
      b.className = 'cat' + (c === activeCat ? ' is-active' : '');
      b.type = 'button'; b.textContent = c; b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', c === activeCat ? 'true' : 'false');
      b.addEventListener('click', () => { activeCat = c; renderCats(); renderGrid(); });
      box.appendChild(b);
    });
  }

  function renderGrid() {
    const grid = document.getElementById('menuGrid');
    const kwL = kw.trim().toLowerCase();
    const list = menu.filter((d) => {
      if (activeCat !== '全部' && d.category !== activeCat) return false;
      if (kwL && !(d.name.toLowerCase().includes(kwL) || (d.description || '').toLowerCase().includes(kwL))) return false;
      return true;
    });
    grid.innerHTML = '';
    if (!list.length) {
      grid.innerHTML = '<div class="empty"><span class="empty__emoji">🍽️</span>没有匹配的菜品</div>';
      return;
    }
    list.forEach((d) => {
      const card = window.Canteen.components.dishCard(d, {
        cartQty: (n) => ctx.store.cartQty(n),
        onAdd: (n, p) => { ctx.store.addItem(n, p); ctx.refreshCart(); renderGrid(); },
        onSet: (n, q) => { ctx.store.setQty(n, q); ctx.refreshCart(); renderGrid(); },
      });
      grid.appendChild(card);
    });
  }

  function mount(c) {
    ctx = c;
    const search = document.getElementById('searchInput');
    search.addEventListener('input', (e) => { kw = e.target.value; renderGrid(); });
    loadMenu();
  }
  function refresh() { loadMenu(); }

  window.Canteen.views.menu = { mount, refresh };
})();
