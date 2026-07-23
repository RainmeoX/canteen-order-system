/* ============================================================
   暖食食堂 · 视图：健康数据关联 + 饮食建议（做深）
   挂载：window.Canteen.views.health.{mount(ctx), refresh()}
   组成：
     ① 健康档案（本地持久 + 患者主索引）
     ② 今日饮食概览（热量/蛋白/糖 vs 目标，进度条）
     ③ 营养评估（NRS-2002 + 能量/蛋白目标）
     ④ 个性化建议（医嘱 + 摄入 + 目标 + 后端建议）
   ============================================================ */
window.Canteen = window.Canteen || {};
window.Canteen.views = window.Canteen.views || {};
(function () {
  let ctx;
  const GOALS = ['低盐', '低糖', '高蛋白', '多喝水', '少油', '高纤维'];

  function parseNutri(n) {
    if (!n) return {};
    if (typeof n === 'object') return n;
    if (typeof n === 'string') { try { return JSON.parse(n) || {}; } catch (e) { return {}; } }
    return {};
  }

  function summarizeIntake(orders) {
    let cal = 0, sugar = 0, protein = 0;
    (orders || []).forEach((o) => (o.items || []).forEach((it) => {
      const n = parseNutri(it.nutrition_info);
      const q = Number(it.quantity) || 0;
      cal += (Number(n.cal) || 0) * q;
      sugar += (Number(n.sugar) || 0) * q;
      protein += (Number(n.protein) || 0) * q;
    }));
    return { cal, sugar, protein };
  }

  function bmi(kg, cm) {
    if (!kg || !cm) return null;
    const m = cm / 100; return kg / (m * m);
  }

  function buildAdvice(o) {
    const out = [];
    const { dietLabel, intake, targets, nrs, suggestions, recs } = o;
    if (dietLabel) out.push({ icon: '🩺', type: 'good', text: '当前饮食类型：<b>' + dietLabel + '</b>。请遵循医嘱限制点餐。' });
    if (intake.cal > targets.cal) out.push({ icon: '🔥', type: 'warn', text: '今日热量约 ' + Math.round(intake.cal) + ' kcal，已超目标 ' + targets.cal + ' kcal，建议下一餐选清淡蒸煮。', recs: (recs || []).map(r => r.name || r).slice(0, 3) });
    else if (intake.cal > 0 && intake.cal < targets.cal * 0.5) out.push({ icon: '🍚', type: 'warn', text: '今日热量仅 ' + Math.round(intake.cal) + ' kcal，偏低，注意补充主食与蛋白。' });
    else out.push({ icon: '✅', type: 'good', text: '今日热量 ' + Math.round(intake.cal) + ' / ' + targets.cal + ' kcal，搭配合理。' });
    if (targets.protein && intake.protein < targets.protein * 0.6) out.push({ icon: '🥚', type: 'warn', text: '蛋白摄入 ' + Math.round(intake.protein) + ' g，低于目标 ' + targets.protein + ' g，建议加一份卤牛肉 / 蛋类。' });
    if (intake.sugar > targets.sugar) out.push({ icon: '🍬', type: 'warn', text: '添加糖 ' + Math.round(intake.sugar) + ' g，超 ' + targets.sugar + ' g，注意甜点。' });
    if (nrs) out.push({ icon: '📋', type: nrs.risk_level && nrs.risk_level.indexOf('高') >= 0 ? 'warn' : 'good', text: '营养风险筛查(NRS-2002)：' + nrs.score + ' 分 · ' + nrs.risk_level + '。' });
    if (nrs && nrs.energy_target) out.push({ icon: '⚡', type: 'good', text: '建议每日能量 ' + Math.round(nrs.energy_target) + ' kcal、蛋白 ' + Math.round(nrs.protein_target) + ' g。' });
    (suggestions || []).forEach((t) => out.push({ icon: '💡', type: 'good', text: t }));
    if (recs && recs.length) out.push({ icon: '🥗', type: 'good', text: '可考虑加餐：', recs: recs.map(r => r.name || r).slice(0, 3) });
    return out;
  }

  function renderProfile() {
    const box = document.getElementById('healthSummary');
    const h = ctx.store.health;
    const p = ctx.store.session && ctx.store.session.patient;
    let html = '';
    if (p) {
      html += '患者：<b>' + (p.name || '—') + '</b> · ' + (ctx.store.session.ward ? ctx.store.session.ward.dept + ' ' + (ctx.store.session.ward.bed_no || '') : '') + '<br>';
      html += '饮食医嘱：<b>' + (ctx.store.session.diet_type_label || '—') + '</b>';
      if (p.diseases && p.diseases.length) html += ' · 病种：' + p.diseases.join('、');
    }
    if (h) {
      const b = bmi(h.weight_kg, h.height_cm);
      html += '<div class="goals">';
      if (b) { const cat = b < 18.5 ? '偏瘦' : b < 24 ? '正常' : b < 28 ? '偏重' : '肥胖'; html += '<span class="goal-chip">BMI ' + b.toFixed(1) + ' · ' + cat + '</span>'; }
      if (h.calorie_target) html += '<span class="goal-chip goal-chip--cal">目标 ' + h.calorie_target + ' kcal</span>';
      if (h.protein_target) html += '<span class="goal-chip">蛋白 ' + h.protein_target + ' g</span>';
      (h.goals || []).forEach((g) => { html += '<span class="goal-chip">' + g + '</span>'; });
      html += '</div>';
    }
    if (!html) html = '尚未完善健康档案。点击下方「编辑」，记录身高体重与目标，饮食建议会更精准。';
    box.innerHTML = html;
  }

  async function load() {
    const s = ctx.store.session;
    if (!s) return;
    const today = await ctx.api.orders(s.user_id, 'today');
    const intake = summarizeIntake(today.data || []);
    let nrs = null, targets = { cal: 2000, protein: 60, sugar: 25 };
    const h = ctx.store.health;
    if (h) { targets.cal = h.calorie_target || targets.cal; targets.protein = h.protein_target || targets.protein; }
    // 营养评估
    const params = {};
    if (s.mode === 'bed' && s.patient_id) params.patient_id = s.patient_id;
    if (h) { if (h.sex) params.sex = h.sex; if (h.weight_kg) params.weight_kg = h.weight_kg; if (h.height_cm) params.height_cm = h.height_cm; if (h.age) params.age = h.age; }
    const na = await ctx.api.nutritionAssess(params);
    if (na.success) {
      nrs = na.nrs2002;
      if (na.energy_target) targets.cal = na.energy_target;
      if (na.protein_target) targets.protein = na.protein_target;
    }
    // 后端饮食建议 + 推荐
    let suggestions = []; let recs = [];
    const ds = await ctx.api.dietarySuggestion(s.user_id);
    if (ds.success && ds.data) {
      suggestions = ds.data.suggestions || [];
      recs = ds.data.recommendations || [];
    }
    // 渲染
    window.Canteen.components.healthPanel.renderMetrics(document.getElementById('healthToday'), intake, targets);
    const advice = buildAdvice({
      dietLabel: s.diet_type_label, intake, targets, nrs, suggestions, recs,
    });
    window.Canteen.components.healthPanel.renderAdvice(document.getElementById('healthAdvice'), advice);
    renderProfile();
  }

  function openEditor() {
    const h = ctx.store.health || {};
    const body = document.createElement('div');
    body.innerHTML =
      '<div class="form-row"><label>体重 (kg)</label><input id="eW" type="number" min="0" step="0.1" value="' + (h.weight_kg || '') + '"></div>' +
      '<div class="form-row"><label>身高 (cm)</label><input id="eH" type="number" min="0" step="0.1" value="' + (h.height_cm || '') + '"></div>' +
      '<div class="form-row"><label>年龄</label><input id="eA" type="number" min="0" step="1" value="' + (h.age || '') + '"></div>' +
      '<div class="form-row"><label>性别</label><select id="eS" class="field__input"><option value="">不填</option><option value="male">男</option><option value="female">女</option></select></div>' +
      '<div class="form-row"><label>每日热量目标 (kcal)</label><input id="eCal" type="number" min="0" step="10" value="' + (h.calorie_target || '') + '"></div>' +
      '<div class="form-row"><label>每日蛋白目标 (g)</label><input id="ePro" type="number" min="0" step="1" value="' + (h.protein_target || '') + '"></div>' +
      '<div class="form-row"><label>饮食目标</label><div class="goal-pick" id="eGoals"></div></div>' +
      '<div class="form-row"><label>忌口 / 过敏（逗号分隔）</label><input id="eAlg" type="text" value="' + (h.allergies || []).join('、') + '"></div>';
    const pick = body.querySelector('#eGoals');
    const cur = h.goals || [];
    GOALS.forEach((g) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'goal-pick__btn' + (cur.indexOf(g) >= 0 ? ' is-on' : '');
      b.textContent = g;
      b.addEventListener('click', () => b.classList.toggle('is-on'));
      pick.appendChild(b);
    });
    if (h.sex) body.querySelector('#eS').value = h.sex;
    const save = document.createElement('button');
    save.className = 'btn btn--solid btn--block'; save.type = 'button'; save.textContent = '保存档案';
    save.addEventListener('click', () => {
      const ng = Array.from(pick.querySelectorAll('.is-on')).map((b) => b.textContent);
      ctx.store.setHealth({
        weight_kg: parseFloat(body.querySelector('#eW').value) || null,
        height_cm: parseFloat(body.querySelector('#eH').value) || null,
        age: parseInt(body.querySelector('#eA').value, 10) || null,
        sex: body.querySelector('#eS').value || null,
        calorie_target: parseInt(body.querySelector('#eCal').value, 10) || null,
        protein_target: parseInt(body.querySelector('#ePro').value, 10) || null,
        goals: ng,
        allergies: body.querySelector('#eAlg').value.split(/[，,]/).map((s) => s.trim()).filter(Boolean),
      });
      window.Canteen.modal.close();
      ctx.toast('健康档案已保存', 'ok');
      load();
    });
    body.appendChild(save);
    window.Canteen.modal.open('编辑健康档案', body);
  }

  function mount(c) {
    ctx = c;
    document.getElementById('healthEditBtn').addEventListener('click', openEditor);
    load();
  }
  function refresh() { if (ctx) load(); }

  window.Canteen.views.health = { mount, refresh };
})();
