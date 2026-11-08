if (location.origin === 'http://127.0.0.1:17653' && location.pathname === '/connect') {
  const token = location.hash.slice(1);
  const button = document.getElementById('connect');
  button?.addEventListener('click', async event => {
    if (!event.isTrusted) return;
    const status = document.getElementById('status');
    if (!/^[a-f0-9]{64}$/.test(token)) {status.textContent = 'In ASUNA, type connect browser to open a fresh connection page.';return;}
    try {
      const response = await chrome.runtime.sendMessage({type:'pair',token});
      status.textContent = response?.ok ? 'Connected. You can return to ASUNA and ask her to open a page.' : response?.error || 'Could not connect.';
      if (response?.ok) {button.disabled = true; history.replaceState(null,'','/connect');}
    } catch (_) {status.textContent = 'Reload this page after loading ASUNA Browser Companion.';}
  });
}
