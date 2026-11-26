(function () {
  const themeButton = document.getElementById('themebtn');
  const languageSelect = document.getElementById('langSelect');

  function setTheme(theme, persist) {
    if (theme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    else document.documentElement.removeAttribute('data-theme');

    if (themeButton) themeButton.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    if (persist) {
      try { localStorage.setItem('aerohealth-theme', theme); } catch (error) {}
    }
  }

  let savedTheme = null;
  try { savedTheme = localStorage.getItem('aerohealth-theme'); } catch (error) {}
  setTheme('light', false);   // light theme only

  if (themeButton) {
    themeButton.addEventListener('click', function () {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      setTheme(next, true);
    });
  }

  function translatedLanguage() {
    const cookie = document.cookie.match(/(?:^|;\s*)googtrans=([^;]+)/);
    if (!cookie) return 'en';
    const parts = decodeURIComponent(cookie[1]).split('/');
    return ['mr', 'hi'].includes(parts[parts.length - 1]) ? parts[parts.length - 1] : 'en';
  }

  if (languageSelect) {
    languageSelect.value = translatedLanguage();
    languageSelect.addEventListener('change', function () {
      const language = languageSelect.value;

      if (language === 'en') {
        document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
        window.location.reload();
        return;
      }

      const googleSelect = document.querySelector('.goog-te-combo');
      if (googleSelect) {
        googleSelect.value = language;
        googleSelect.dispatchEvent(new Event('change'));
      } else {
        document.cookie = `googtrans=/en/${language}; path=/`;
        window.location.reload();
      }
    });
  }

  window.googleTranslateElementInit = function () {
    if (!window.google || !window.google.translate || !languageSelect) return;
    new window.google.translate.TranslateElement({
      pageLanguage: 'en',
      includedLanguages: 'en,mr,hi',
      autoDisplay: false
    }, 'google_translate_element');
    languageSelect.value = translatedLanguage();
  };
})();