/* ============================================================
   暖食食堂 · API 层（统一 fetch 封装：超时 / 错误归一 / 重试）
   挂载：window.Canteen.api
   ============================================================ */
window.Canteen = window.Canteen || {};
Canteen.api = (function () {
  const TIMEOUT = 12000;

  async function request(path, opts) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT);
    try {
      const res = await fetch(path, {
        headers: { 'Content-Type': 'application/json' },
        signal: ctrl.signal,
        ...opts,
      });
      clearTimeout(timer);
      let data = {};
      try { data = await res.json(); } catch (e) { /* 忽略解析错误 */ }
      if (!res.ok) {
        return { success: false, message: data.message || `请求失败 (${res.status})`, status: res.status };
      }
      return data;
    } catch (e) {
      clearTimeout(timer);
      if (e && e.name === 'AbortError') return { success: false, message: '请求超时，请稍后重试' };
      return { success: false, message: '网络异常：' + (e && e.message ? e.message : '无法连接服务') };
    }
  }

  const post = (p, body) => request(p, { method: 'POST', body: JSON.stringify(body || {}) });
  const get = (p) => request(p);

  return {
    // 床头码进入：返回病区/床位/患者档案 + 按医嘱过滤后的菜单
    bedEnter: (token) => post('/api/v1/bed/enter', { bed_qr_token: token }),
    // 医嘱规则引擎
    dietRules: (diet_type) => get('/api/v1/diet/rules?diet_type=' + encodeURIComponent(diet_type || 'normal')),
    // 统一下单（支持 fulfillment_mode）
    placeOrder: (payload) => post('/api/v1/orders', payload),
    // 订单查询（今日/历史），含履约模式与配送状态
    orders: (user_id, scope, dates) => {
      let p = '/api/v1/orders?user_id=' + encodeURIComponent(user_id) + '&scope=' + (scope || 'today');
      if (dates && dates.start) p += '&start_date=' + encodeURIComponent(dates.start);
      if (dates && dates.end) p += '&end_date=' + encodeURIComponent(dates.end);
      return get(p);
    },
    // 营养评估（NRS-2002 + 能量/蛋白目标）
    nutritionAssess: (params) => {
      const q = new URLSearchParams();
      Object.keys(params || {}).forEach((k) => {
        const v = params[k];
        if (v !== '' && v != null) q.set(k, v);
      });
      return get('/api/v1/nutrition/assess?' + q.toString());
    },
    // 配送单（装车表/发餐表）
    deliveries: (status) => get('/api/v1/deliveries' + (status ? '?status=' + encodeURIComponent(status) : '')),
    // 配送 marking
    markDelivery: (id, status) => post('/api/v1/deliveries/' + id + '/mark', { status }),
    // 旧端点：饮食建议（今日热量/糖分 + 文本建议 + 推荐菜）
    dietarySuggestion: (user_id) => get('/api/dietary_suggestion?user_id=' + encodeURIComponent(user_id)),
    // 旧端点：通用菜单（职工/访客自取）
    menu: () => get('/api/menu'),
  };
})();
