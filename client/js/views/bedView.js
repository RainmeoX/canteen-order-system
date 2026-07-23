/* ============================================================
   暖食食堂 · 视图：床头码进入（一床一码）
   挂载：window.Canteen.views.bed.mount(entryEl, ctx)
   两种身份入口：
     ① 床头码进入  → /api/v1/bed/enter（自动定位科室/床位/患者 + 医嘱过滤菜单）
     ② 职工/访客自取 → 普通点餐（fulfillment_mode=pickup）
   ============================================================ */
window.Canteen = window.Canteen || {};
window.Canteen.views = window.Canteen.views || {};
(function () {
  const DEMO_TOKENS = [
    { token: 'QR-END01', label: '内分泌科 · 8F · 糖尿病饮食' },
    { token: 'QR-CAR03', label: '心内科 · 低盐低脂' },
    { token: 'QR-SUR02', label: '普外科 · 流质膳食' },
    { token: 'QR-REN05', label: '肾内科 · 低蛋白' },
  ];

  function mount(entryEl, ctx) {
    const card = document.createElement('div');
    card.className = 'entry__card';

    const logo = document.createElement('div');
    logo.className = 'entry__logo'; logo.textContent = '🏥';
    const title = document.createElement('h1');
    title.className = 'entry__title'; title.textContent = '暖食食堂 · 住院点餐';
    const sub = document.createElement('p');
    sub.className = 'entry__sub'; sub.textContent = '扫床头码或输入床位码，按医嘱为你呈现可点餐品';

    const group = document.createElement('div');
    group.className = 'entry__group';

    // ① 床头码
    const bedRow = document.createElement('div');
    bedRow.className = 'form-row';
    const bedLabel = document.createElement('label'); bedLabel.textContent = '床头码 / 床位码';
    const bedInput = document.createElement('input');
    bedInput.type = 'text'; bedInput.placeholder = '如 QR-END01'; bedInput.setAttribute('list', 'bedTokens');
    bedInput.setAttribute('autocomplete', 'off');
    const dl = document.createElement('datalist'); dl.id = 'bedTokens';
    DEMO_TOKENS.forEach((t) => {
      const o = document.createElement('option'); o.value = t.token; o.label = t.label; dl.appendChild(o);
    });
    const bedBtn = document.createElement('button');
    bedBtn.className = 'btn btn--solid btn--block'; bedBtn.type = 'button'; bedBtn.textContent = '扫码进入 · 按医嘱点餐';
    bedBtn.addEventListener('click', async () => {
      const token = bedInput.value.trim();
      if (!token) { ctx.toast('请输入床位码', 'err'); return; }
      bedBtn.disabled = true; bedBtn.textContent = '定位中…';
      const r = await ctx.api.bedEnter(token);
      bedBtn.disabled = false; bedBtn.textContent = '扫码进入 · 按医嘱点餐';
      if (!r.success) { ctx.toast(r.message || '进入失败', 'err'); return; }
      const s = {
        mode: 'bed',
        bed_qr_token: token,
        user_id: r.patient ? r.patient.patient_id : null,
        patient_id: r.patient ? r.patient.patient_id : null,
        patient: r.patient,
        ward: r.ward,
        diet_type: r.diet_type,
        diet_type_label: r.diet_type_label,
        constraints: r.constraints,
      };
      if (!s.user_id) { ctx.toast('该患者尚未建登录账号，请联系护士站', 'err'); return; }
      ctx.setSession(s);
      ctx.toast((r.ward.dept || '床位') + ' · ' + (r.diet_type_label || '') + ' 已就绪', 'ok');
      ctx.navigate('menu');
    });
    bedRow.appendChild(bedLabel); bedRow.appendChild(bedInput); bedRow.appendChild(dl); bedRow.appendChild(bedBtn);

    const orEl = document.createElement('div');
    orEl.className = 'entry__or'; orEl.textContent = '或';

    // ② 职工 / 访客自取
    const staffRow = document.createElement('div');
    staffRow.className = 'form-row';
    const staffLabel = document.createElement('label'); staffLabel.textContent = '工号 / 访客 ID（自取）';
    const staffInput = document.createElement('input');
    staffInput.type = 'text'; staffInput.value = 'U1001'; staffInput.placeholder = '如 U1001';
    const staffBtn = document.createElement('button');
    staffBtn.className = 'btn btn--ghost btn--block'; staffBtn.type = 'button'; staffBtn.textContent = '进入 · 食堂自取';
    staffBtn.addEventListener('click', () => {
      const uid = staffInput.value.trim();
      if (!uid) { ctx.toast('请输入工号 / ID', 'err'); return; }
      ctx.setSession({ mode: 'staff', user_id: uid });
      ctx.toast('已以自取模式进入', 'ok');
      ctx.navigate('menu');
    });
    staffRow.appendChild(staffLabel); staffRow.appendChild(staffInput); staffRow.appendChild(staffBtn);

    const hint = document.createElement('p');
    hint.className = 'entry__hint';
    hint.innerHTML = '演示床位码：<code>QR-END01</code> <code>QR-CAR03</code> <code>QR-SUR02</code> <code>QR-REN05</code>';

    group.appendChild(bedRow); group.appendChild(orEl); group.appendChild(staffRow);
    card.appendChild(logo); card.appendChild(title); card.appendChild(sub);
    card.appendChild(group); card.appendChild(hint);
    entryEl.innerHTML = ''; entryEl.appendChild(card);
  }

  window.Canteen.views.bed = { mount };
})();
