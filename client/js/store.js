/* ============================================================
   暖食食堂 · 状态层（会话 / 购物车 / 健康档案 · localStorage 持久）
   挂载：window.Canteen.store
   ============================================================ */
window.Canteen = window.Canteen || {};
Canteen.store = (function () {
  const LS = {
    session: 'canteen.session.v1',
    cart: 'canteen.cart.v1',
    health: 'canteen.health.v1',
  };

  function read(k, def) {
    try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; }
    catch (e) { return def; }
  }
  function write(k, v) {
    try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* 隐私模式忽略 */ }
  }

  const SESSION_DEFAULT = null;       // {mode, bed_qr_token?, user_id, patient_id?, ward?, diet_type?, ...}
  const CART_DEFAULT = {};            // {dish_name: {name, price, qty}}
  const HEALTH_DEFAULT = null;        // {weight_kg,height_cm,age,sex,calorie,protein,goals[],allergies[]}

  const state = {
    session: read(LS.session, SESSION_DEFAULT),
    cart: read(LS.cart, CART_DEFAULT),
    health: read(LS.health, HEALTH_DEFAULT),
  };

  return {
    /* ---------- 会话 ---------- */
    get session() { return state.session; },
    setSession(s) { state.session = s; write(LS.session, s); },
    clearSession() { state.session = null; write(LS.session, null); },

    /* ---------- 购物车 ---------- */
    get cart() { return state.cart; },
    cartCount() { return Object.keys(state.cart).reduce((a, k) => a + state.cart[k].qty, 0); },
    cartTotal() { return Object.keys(state.cart).reduce((a, k) => a + state.cart[k].qty * state.cart[k].price, 0); },
    addItem(name, price) {
      const c = state.cart[name] || { name, price, qty: 0 };
      c.qty += 1; c.price = price; state.cart[name] = c; write(LS.cart, state.cart);
    },
    setQty(name, qty) {
      if (qty <= 0) { delete state.cart[name]; }
      else { const price = (state.cart[name] || { price: 0 }).price; state.cart[name] = { name, price, qty }; }
      write(LS.cart, state.cart);
    },
    cartQty(name) { return state.cart[name] ? state.cart[name].qty : 0; },
    clearCart() { state.cart = {}; write(LS.cart, {}); },

    /* ---------- 健康档案 ---------- */
    get health() { return state.health; },
    setHealth(h) { state.health = h; write(LS.health, h); },
  };
})();
