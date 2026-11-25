(function () {
  const root = document.getElementById('kyc-section');
  if (!root) return;
  const form = root.closest('form');
  const val = name => form.querySelector(`[name="kyc_${name}"]`)?.value || '';
  const hide = (id, yes) => { const el = document.getElementById(id); if (el) el.hidden = !yes; };

  function syncConditional() {
    const gender = val('gender');
    const age = val('age_group');
    const adultPregnancyRange = ['18_30', '31_45'].includes(age);
    const showPregnancy = gender === 'female' && adultPregnancyRange;
    hide('kyc-pregnancy-block', showPregnancy);
    hide('kyc-trimester-block', showPregnancy && val('pregnant') === 'yes');
    hide('kyc-complications-block', showPregnancy && val('pregnant') === 'yes');
    hide('kyc-senior-block', age === '60_plus');
    const childSelected = [...form.querySelectorAll('[name="kyc_family_members"]:checked')].some(x => x.value === 'Child');
    hide('kyc-child-block', childSelected);
  }
  root.querySelectorAll('[name="kyc_gender"], [name="kyc_age_group"], [name="kyc_pregnant"], [name="kyc_family_members"]').forEach(el => el.addEventListener('change', syncConditional));

  // Restore saved KYC answers into the controls when the account page is reopened.
  try {
    const data = JSON.parse(document.getElementById('kyc-existing-data')?.textContent || '{}');
    Object.entries(data).forEach(([key, value]) => {
      const controls = [...form.querySelectorAll(`[name="kyc_${key}"]`)];
      if (!controls.length) return;
      const values = Array.isArray(value) ? value.map(String) : [String(value)];
      controls.forEach(control => {
        if (control.type === 'checkbox' || control.type === 'radio') control.checked = values.includes(control.value);
        else control.value = values[0];
      });
    });
  } catch (_) { /* Existing profile answers are optional; leave controls at defaults. */ }
  syncConditional();

  // Basic-only consent is mutually exclusive with the two optional data consents.
  const basicOnly = form.querySelector('[name="kyc_basic_only"]');
  const consentBoxes = [...form.querySelectorAll('[name="kyc_health_consent"], [name="kyc_location_consent"]')];
  basicOnly?.addEventListener('change', () => { if (basicOnly.checked) consentBoxes.forEach(box => { box.checked = false; }); });
  consentBoxes.forEach(box => box.addEventListener('change', () => { if (box.checked && basicOnly) basicOnly.checked = false; }));

  // Keep mutually exclusive answers exclusive in multi-select groups (e.g. None).
  root.querySelectorAll('.kyc-checks').forEach(group => {
    const boxes = [...group.querySelectorAll('input[type="checkbox"]')];
    boxes.forEach(box => box.addEventListener('change', () => {
      if (!box.checked) return;
      const isNone = ['None', 'Prefer not to say'].includes(box.value);
      if (isNone) boxes.forEach(other => { if (other !== box) other.checked = false; });
      else boxes.filter(other => ['None', 'Prefer not to say'].includes(other.value)).forEach(other => other.checked = false);
    }));
  });

  const progress = document.getElementById('kyc-progress');
  const label = document.getElementById('kyc-progress-label');
  const stages = [...root.querySelectorAll('.kyc-stage')];
  function updateProgress() {
    const completed = stages.filter(stage => {
      const controls = [...stage.querySelectorAll('input,select,textarea')].filter(el => !el.disabled && el.type !== 'hidden');
      return controls.some(el => el.type === 'checkbox' || el.type === 'radio' ? el.checked : !!el.value);
    }).length;
    progress.style.width = `${Math.round(completed / stages.length * 100)}%`;
    label.textContent = `${completed} of ${stages.length} sections started`;
  }
  root.addEventListener('input', updateProgress);
  root.addEventListener('change', updateProgress);
  updateProgress();
})();
