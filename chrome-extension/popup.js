async function refreshStatus() {
  const {pairing}=await chrome.storage.local.get('pairing');
  const status = document.getElementById('status');
  if (!pairing?.token) {status.textContent = 'Not paired yet.';return;}
  try {
    const response = await fetch('http://127.0.0.1:17653/status',{method:'POST',
      headers:{'Authorization':'Bearer '+pairing.token,'Content-Type':'application/json'},body:'{}',signal:AbortSignal.timeout(2000)});
    if(response.status===403){status.textContent='Pairing needs refreshing. Type connect browser in ASUNA.';return;}
    const state = response.ok ? await response.json() : {};
    status.textContent = state.connected ? 'Connected to your local ASUNA.' : 'Paired. Press Reconnect now.';
  } catch (_) {status.textContent = 'Paired. Open ASUNA to connect.';}
}
refreshStatus();
document.getElementById('reconnect').addEventListener('click',async()=>{
  const response=await chrome.runtime.sendMessage({type:'wake'});
  if(response?.error){document.getElementById('status').textContent=response.error;return;}
  document.getElementById('status').textContent='Reconnecting…';
  setTimeout(refreshStatus,700);
});
document.getElementById('disconnect').addEventListener('click',async () => {
  await chrome.runtime.sendMessage({type:'disconnect'});
  document.getElementById('status').textContent = 'Disconnected from ASUNA.';
});
