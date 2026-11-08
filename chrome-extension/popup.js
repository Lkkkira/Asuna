chrome.storage.local.get('pairing').then(async ({pairing}) => {
  const status = document.getElementById('status');
  if (!pairing?.token) {status.textContent = 'Not paired yet.';return;}
  try {
    const response = await fetch('http://127.0.0.1:17653/status',{method:'POST',
      headers:{'Authorization':'Bearer '+pairing.token,'Content-Type':'application/json'},body:'{}',signal:AbortSignal.timeout(2000)});
    const state = response.ok ? await response.json() : {};
    status.textContent = state.connected ? 'Connected to your local ASUNA.' : 'Paired. Type connect browser in ASUNA to reconnect.';
  } catch (_) {status.textContent = 'Paired. Open ASUNA to connect.';}
});
document.getElementById('disconnect').addEventListener('click',async () => {
  await chrome.runtime.sendMessage({type:'disconnect'});
  document.getElementById('status').textContent = 'Disconnected from ASUNA.';
});
