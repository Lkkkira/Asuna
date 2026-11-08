/* Packaged page functions only; no model-provided code. */
async function runPageCommand(command, args) {
  try {
    let value;
    if (command === 'observePage') value = observePage(...args);
    else if (command === 'actOnPage') value = await actOnPage(...args);
    else throw Error('Unsupported page command.');
    return {ok:true,value};
  } catch (error) {
    return {ok:false,error:String(error.message || error)};
  }
}
async function actOnPage(operation, payload) {
  const visible = e => !!(e && e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && !e.disabled);
  if (payload.url && location.href !== payload.url) throw Error('The page changed. Read it again.');
  if (['click', 'fill', 'search'].includes(operation)) {
    const item = payload.item;
    if (!item || !/^[a-f0-9-]+$/.test(item.marker)) throw Error('Invalid observed target.');
    const matches = document.querySelectorAll('[data-asuna-target="' + item.marker + '"]');
    if (matches.length !== 1 || !visible(matches[0])) throw Error('That control changed. Read the page again.');
    const e = matches[0], tag = e.tagName.toLowerCase();
    const name = (e.getAttribute('aria-label') || e.labels?.[0]?.innerText || e.innerText || e.getAttribute('placeholder') || e.getAttribute('title') || (['submit','button','reset'].includes(e.type) ? e.value : '') || e.name || e.id || '').trim().replace(/\s+/g, ' ').slice(0,180);
    if (name !== item.name || (e.type || '') !== item.type || (tag === 'a' ? e.href : '') !== item.href)
      throw Error('That control changed. Read the page again.');
    if (operation === 'click') {
      if (tag === 'a' && !/^https?:\/\//.test(e.href)) throw Error('Only ordinary web links are supported.');
      e.click();
    } else {
      if (item.role !== 'field' || ['password','file','hidden'].includes(e.type) ||
          /password|credit.?card|cvv|otp|one.time|security.code|cc-/i.test(name + ' ' + (e.autocomplete || '')))
        throw Error('Enter authentication, payment and upload details manually in Chrome.');
      if (tag === 'select') throw Error('Choose dropdown values manually for now.');
      e.focus();
      if (e.isContentEditable) e.textContent = payload.value;
      else {
        const prototype = tag === 'textarea' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(prototype, 'value').set.call(e, payload.value);
      }
      e.dispatchEvent(new Event('input', {bubbles:true}));
      e.dispatchEvent(new Event('change', {bubbles:true}));
      if (operation === 'search') {
        if (e.form) e.form.requestSubmit();
        else for (const type of ['keydown','keyup']) e.dispatchEvent(new KeyboardEvent(type, {key:'Enter',code:'Enter',bubbles:true}));
      }
    }
    return {};
  }
  if (operation === 'scroll') {
    if (!['up','down','top','bottom'].includes(payload.value)) throw Error('Choose up/down/top/bottom.');
    const d = payload.value;
    d === 'top' ? scrollTo(0,0) : d === 'bottom' ? scrollTo(0,document.body.scrollHeight) : scrollBy(0,d === 'up' ? -700 : 700);
    return {};
  }
  if (operation === 'find') {
    const needle = payload.value.toLocaleLowerCase();
    const e = [...document.querySelectorAll('p,h1,h2,h3,h4,span,a,button,label,li')].find(e => visible(e) && e.innerText.toLocaleLowerCase().includes(needle));
    if (!e) throw Error('That text was not found on the page.');
    e.scrollIntoView({block:'center'});
    return {};
  }
  if (operation === 'media') {
    if (!['play','pause','mute','unmute'].includes(payload.value)) throw Error('Unsupported media action.');
    let e = document.querySelector('video,audio');
    const deadline = performance.now() + 8000;
    while (!e && performance.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve,200));
      e = document.querySelector('video,audio');
    }
    if (!e) throw Error('No HTML video/audio was found.');
    if (payload.url && location.href !== payload.url) throw Error('The page changed. Read it again.');
    if (payload.value === 'play') await e.play();
    else if (payload.value === 'pause') e.pause();
    else e.muted = payload.value === 'mute';
    return {paused:e.paused,muted:e.muted};
  }
  throw Error('Unsupported page operation.');
}
function observePage(token) {
 const visible = e => !!(e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && !e.disabled && !e.closest('[aria-hidden="true"]'));
 const seen = new Set(), items = [];
 const inView=e=>{const r=e.getBoundingClientRect();return r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth;};
 const nodes=[...document.querySelectorAll('a[href],button,input:not([type=hidden]),textarea,select,[role=button],[contenteditable=true]')];
 nodes.sort((a,b)=>Number(inView(b))-Number(inView(a)));
 for (const e of nodes) {
  if (!visible(e)) continue;
  const tag=e.tagName.toLowerCase(), buttonInput=tag==='input'&&['submit','button','reset'].includes(e.type);
  const role=tag==='a'?'link':!buttonInput&&(tag==='input'||tag==='textarea'||tag==='select'||e.isContentEditable)?'field':'button';
  const name=(e.getAttribute('aria-label')||e.labels?.[0]?.innerText||e.innerText||e.getAttribute('placeholder')||e.getAttribute('title')||(buttonInput?e.value:'')||e.name||e.id||'').trim().replace(/\s+/g,' ').slice(0,180);
  if (!name && role!=='field') continue;
  const href=tag==='a'?e.href:'';
  if (role==='link' && (!/^https?:/.test(href)||seen.has(href))) continue;
  if (href) seen.add(href);
  const marker=token+'-'+items.length; e.setAttribute('data-asuna-target',marker);
  const ad=!!e.closest('ytd-ad-slot-renderer,ytd-promoted-video-renderer,[data-text-ad],[data-ad],.ads,.sponsored');
  const video=!ad && (/youtube\.com\/watch\?|youtu\.be\/|vimeo\.com\/\d|dailymotion\.com\/video\/|\.(mp4|webm)(\?|$)/i.test(href));
  const result=!ad && (video || !!e.querySelector('h2,h3') || !!e.closest('.search-result,.result,.b_algo,.tF2Cxc,ytd-video-renderer'));
  items.push({id:items.length+1,role,name,href,type:e.type||'',marker,video,result});
  if(items.length>=120) break;
 }
 return {url:location.href,title:document.title,items,text:(document.body?.innerText||'').slice(0,12000)};
}
