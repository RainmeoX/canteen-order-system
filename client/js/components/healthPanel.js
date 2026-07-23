/* ============================================================
   暖食食堂 · 组件：健康面板（指标进度条 / 个性化建议）
   挂载：window.Canteen.components.healthPanel.{renderMetrics, renderAdvice}
   ============================================================ */
window.Canteen = window.Canteen || {};
window.Canteen.components = window.Canteen.components || {};
(function () {
  // 今日摄入 vs 目标，渲染进度条
  function renderMetrics(container, intake, targets) {
    container.innerHTML = '';
    const rows = [
      { key: 'cal', label: '热量', unit: 'kcal', val: intake.cal || 0, target: targets.cal || 2000, warn: true },
      { key: 'protein', label: '蛋白', unit: 'g', val: intake.protein || 0, target: targets.protein || 60, warn: false },
      { key: 'sugar', label: '添加糖', unit: 'g', val: intake.sugar || 0, target: targets.sugar || 25, warn: true },
    ];
    rows.forEach((r) => {
      const pct = r.target > 0 ? Math.min(100, Math.round((r.val / r.target) * 100)) : 0;
      const over = r.warn && r.val > r.target;
      const m = document.createElement('div');
      m.className = 'metric';
      m.innerHTML =
        '<div class="metric__top"><span>' + r.label + '</span>' +
        '<b>' + Math.round(r.val) + ' / ' + r.target + ' ' + r.unit + '</b></div>' +
        '<div class="bar"><div class="bar__fill' + (over ? ' is-over' : '') + '" style="width:' + pct + '%"></div></div>';
      container.appendChild(m);
    });
  }

  function renderAdvice(container, list) {
    container.innerHTML = '';
    if (!list || !list.length) {
      const p = document.createElement('p');
      p.className = 'health__summary';
      p.textContent = '暂无特别建议，保持当前搭配即可。';
      container.appendChild(p);
      return;
    }
    list.forEach((a) => {
      const item = document.createElement('div');
      item.className = 'advice__item' + (a.type === 'warn' ? ' is-warn' : a.type === 'good' ? ' is-good' : '');
      const ico = document.createElement('span');
      ico.className = 'advice__ico'; ico.textContent = a.icon || '💡';
      const txt = document.createElement('div');
      txt.innerHTML = '<div>' + (a.text || '') + '</div>';
      if (a.recs && a.recs.length) {
        const recs = document.createElement('div');
        recs.className = 'advice__rec';
        a.recs.forEach((r) => { const t = document.createElement('span'); t.className = 'tag tag--sage'; t.textContent = r; recs.appendChild(t); });
        txt.appendChild(recs);
      }
      item.appendChild(ico); item.appendChild(txt);
      container.appendChild(item);
    });
  }

  window.Canteen.components.healthPanel = { renderMetrics, renderAdvice };
})();
