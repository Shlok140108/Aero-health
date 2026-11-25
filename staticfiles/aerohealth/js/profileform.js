/* Place at: backend/dashboard/static/aerohealth/js/profileform.js
 * Shared by the sign-up wizard (/signup/) and the Account page (/account/).
 *  - shows the pregnancy questions only for women aged 13-55, trimester only when pregnant
 *  - "None of these" excludes the other health conditions
 *  - city suggestions from /api/cities/ and a "use my location" button
 *  - on the sign-up page (form[data-wizard]) runs the 5-step flow
 */
(function () {
  const $ = id => document.getElementById(id);
  const form = $('profile-form');
  if (!form) return;
  const f = n => form.elements[n];

  /* ---- pregnancy questions ---- */
  function syncPregnancy() {
    const age = parseInt(f('age').value, 10);
    const show = f('gender').value === 'F' && age >= 13 && age <= 55;
    $('preg-block').hidden = !show;
    const pregnant = show && (form.querySelector('input[name="pregnancy_status"]:checked') || {}).value === 'pregnant';
    $('tri-block').hidden = !pregnant;
  }
  ['gender', 'age'].forEach(n => { f(n).addEventListener('input', syncPregnancy); f(n).addEventListener('change', syncPregnancy); });
  form.querySelectorAll('input[name="pregnancy_status"]').forEach(r => r.addEventListener('change', syncPregnancy));
  syncPregnancy();

  /* ---- "None of these" is exclusive ---- */
  const conds = [...form.querySelectorAll('input[name="conditions"]')];
  conds.forEach(c => c.addEventListener('change', () => {
    if (!c.checked) return;
    conds.forEach(o => { if (o !== c && ((c.value === 'none') || (o.value === 'none'))) o.checked = false; });
  }));

  /* ---- city suggestions + live location ---- */
  fetch('/api/cities/').then(r => r.json()).then(d => {
    const list = $('city-list'), cities = d.cities || [];
    list.innerHTML = cities.map(c => `<option value="${c.name.replace(/"/g, '&quot;')}"></option>`).join('');
    f('city').addEventListener('change', () => {
      const c = cities.find(x => x.name.toLowerCase() === f('city').value.trim().toLowerCase());
      if (c) { f('state').value = c.state || ''; f('lat').value = c.lat; f('lon').value = c.lon; }
      else { f('lat').value = ''; f('lon').value = ''; }          // typed by hand: no coordinates
    });
  }).catch(() => {});

  const geoBtn = $('geo-btn'), msg = $('geo-msg');
  geoBtn.addEventListener('click', () => {
    if (!navigator.geolocation) { msg.textContent = 'Location is not available in this browser. Please type your city.'; return; }
    msg.textContent = 'Finding you…';
    navigator.geolocation.getCurrentPosition(pos => {
      const lat = +pos.coords.latitude.toFixed(4), lon = +pos.coords.longitude.toFixed(4);
      f('lat').value = lat; f('lon').value = lon;
      msg.textContent = 'Got it. Looking up the place name…';
      fetch(`/api/reverse/?lat=${lat}&lon=${lon}`).then(r => r.json()).then(d => {
        if (d.resolved) f('city').value = d.label;
        else if (!f('city').value) f('city').value = d.label;
        msg.textContent = 'Location saved ✓ (only rounded coordinates are stored).';
      }).catch(() => { msg.textContent = 'Location saved ✓ Please type your city name too.'; });
    }, () => { msg.textContent = 'We could not get your location. Please type your city instead.'; },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
  });

  /* ---- wizard (sign-up only) ---- */
  if (!form.hasAttribute('data-wizard')) return;
  document.documentElement.classList.add('js');
  const steps = [...form.querySelectorAll('.step')];
  $('steps').innerHTML = steps.map(() => '<i></i>').join('');
  const dots = [...document.querySelectorAll('#steps i')];
  const back = $('back'), next = $('next'), finish = $('finish'), label = $('step-label');
  let cur = Math.max(0, steps.findIndex(s => s.querySelector('.err:not(.js-err)')));         // start at the first step with a server error

  function show(i) {
    cur = i;
    steps.forEach((s, k) => s.classList.toggle('on', k === i));
    dots.forEach((d, k) => d.classList.toggle('done', k <= i));
    label.textContent = `Step ${i + 1} of ${steps.length}`;
    back.hidden = i === 0; next.hidden = i === steps.length - 1; finish.hidden = i !== steps.length - 1;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function problem(el, text) { el.setCustomValidity(text); el.reportValidity(); el.addEventListener('input', () => el.setCustomValidity(''), { once: true }); }

  function stepOk(i) {
    const s = steps[i];
    for (const el of s.querySelectorAll('input:not([type=hidden]), select, textarea')) {
      if (el.closest('[hidden]')) continue;
      if (!el.checkValidity()) { el.reportValidity(); return false; }
    }
    if (s.dataset.check === 'account' && f('password1').value !== f('password2').value) { problem(f('password2'), "Passwords don't match."); return false; }
    if (s.dataset.check === 'health' && !conds.some(c => c.checked)) {
      const e = s.querySelector('.js-err'); e.textContent = "Choose at least one, or 'None of these'."; e.hidden = false; return false;
    }
    if (s.dataset.check === 'work' && !$('preg-block').hidden) {
      if (!form.querySelector('input[name="pregnancy_status"]:checked')) { alert('Please answer the pregnancy question.'); return false; }
      if (!$('tri-block').hidden && !f('trimester').value) { problem(f('trimester'), 'Please choose your trimester.'); return false; }
    }
    return true;
  }

  next.addEventListener('click', () => { if (stepOk(cur)) show(cur + 1); });
  back.addEventListener('click', () => show(cur - 1));
  form.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT' && cur < steps.length - 1) { e.preventDefault(); next.click(); }
  });
  form.addEventListener('submit', e => { if (!stepOk(cur)) e.preventDefault(); });
  show(cur);
})();
