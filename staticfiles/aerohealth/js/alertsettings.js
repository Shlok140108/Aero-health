(() => {
  const button = document.getElementById('verify-phone-btn');
  if (!button) return;
  const csrf = () => document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] || '';
  const post = async (url, body = {}) => {
    const response = await fetch(url, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':csrf()}, body:JSON.stringify(body)});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Request failed');
    return data;
  };
  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      await post('/api/alerts/phone/request-otp/');
      const code = window.prompt('Enter the 6-digit code sent to your phone:');
      if (!code) return;
      await post('/api/alerts/phone/confirm-otp/', {code:code.trim()});
      const status = document.getElementById('phone-verification-status');
      if (status) status.textContent = 'Phone verification status: Verified';
      button.remove();
      window.alert('Phone verified. SMS and voice can now be used if enabled.');
    } catch (error) {
      window.alert(error.message);
    } finally {
      if (document.body.contains(button)) button.disabled = false;
    }
  });
})();
