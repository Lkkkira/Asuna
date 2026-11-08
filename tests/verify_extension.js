/* Exercise the packaged worker with a fake Chrome API, without a user profile. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {webcrypto} = require('node:crypto');
const folder = path.join(__dirname,'..','chrome-extension');
const listeners = {};
let url = 'https://fixture.test/', activeId = 1, calls = [], scriptFailure = null, extraItems = [];
const pools = {local:{},session:{}};
const storage = pool => ({get:async key=>({[key]:pool[key]}),set:async values=>Object.assign(pool,values),remove:async key=>delete pool[key]});
const current = () => ({id:activeId,url,status:'complete',windowId:1,title:'Fixture'});
const snapshot = token => ({url,title:'Fixture',text:'Untrusted reference text',items:[
  {id:1,role:'link',name:'First result',href:'https://fixture.test/next',type:'',marker:token+'-0',result:true,video:false},
  {id:2,role:'button',name:'Submit',href:'',type:'submit',marker:token+'-1'},
  {id:3,role:'field',name:'Search',href:'',type:'search',marker:token+'-2'},
  {id:4,role:'field',name:'Password',href:'',type:'password',marker:token+'-3'},
  ...extraItems.map((item,index)=>({...item,id:index+5,marker:token+'-'+(index+4)}))]});
const sandbox = {URL,AbortSignal,crypto:webcrypto,console,setTimeout:fn=>{queueMicrotask(fn);return 1;},
  fetch:async()=>{throw Error('No network in this test');},chrome:{
    storage:{local:storage(pools.local),session:storage(pools.session)},
    runtime:{getURL:p=>'chrome-extension://'+'a'.repeat(32)+'/'+p,
      onMessage:{addListener:fn=>listeners.message=fn},onInstalled:{addListener(){}},onStartup:{addListener(){}}},
    alarms:{create(){},onAlarm:{addListener(){}}},windows:{update:async()=>{}},
    tabs:{query:async()=>[current()],get:async()=>current(),
      create:async options=>{url=options.url;return current();},
      update:async id=>{activeId=id;return current();},goBack:async()=>{},goForward:async()=>{},reload:async()=>{}},
    scripting:{executeScript:async ({files,args})=>{
      if (files) return [];
      if (scriptFailure) return [{result:scriptFailure}];
      const [command,values] = args;
      if (command === 'observePage') return [{result:{ok:true,value:snapshot(values[0])}}];
      calls.push(values);
      if (values[0] === 'like') {extraItems[0].pressed='true';return [{result:{ok:true,value:{liked:true}}}];}
      return [{result:{ok:true,value:values[0]==='media'?{paused:true,muted:false}:{}}}];
    }}}
};
const context = vm.createContext(sandbox);
sandbox.importScripts = file=>vm.runInContext(fs.readFileSync(path.join(folder,file),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(folder,'background.js'),'utf8'),context);
const run = (action,text='',number=0)=>sandbox.perform({action,text,number});
(async()=>{
  const read = await run('read');
  assert.match(read.reference,/Untrusted reference text/);
  assert.ok(read.snapshot.token);
  const review = await run('click','Submit');
  assert.ok(review.confirm && review.ticket);
  assert.equal(calls.length,0);
  await run('approve',review.ticket);
  assert.equal(calls.length,1);
  await assert.rejects(run('approve',review.ticket),/no longer current/);
  const stale = await run('fill',JSON.stringify({value:'cats'}),3);
  await run('read');
  await assert.rejects(run('approve',stale.ticket),/no longer current/);
  await assert.rejects(run('fill',JSON.stringify({value:'secret'}),4),/authentication/);
  const changed = await run('click','Submit');
  activeId = 2;
  await assert.rejects(run('approve',changed.ticket),/no longer current/);
  activeId = 1;
  await run('open_item','result',1);
  assert.equal(calls.at(-1)[0],'click');
  await run('search','cats');
  assert.equal(pools.session.control.pending.operation,'search');
  for (const bad of ['javascript:alert(1)','file:///C:/test','https://user:pass@fixture.test'])
    await assert.rejects(run('open',bad),/http/);
  await assert.rejects(run('evaluate','dangerous()'),/Unsupported/);
  scriptFailure = {ok:false,error:'No HTML video/audio was found.'};
  await assert.rejects(run('media','pause'),/No HTML video/);
  scriptFailure = {};
  await assert.rejects(run('read'),/page changed or Chrome/);
  scriptFailure = null;
  url = 'https://www.youtube.com/watch?v=fixture';
  extraItems = [
    {role:'button',name:'like this video along with 191,712 other people',type:'',href:'',pressed:'false'},
    {role:'button',name:'Like this comment along with 10 other people',type:'',href:'',pressed:'false'},
    {role:'button',name:'Dislike this video',type:'',href:'',pressed:'false'},
    {role:'field',name:'Like',type:'text',href:''}];
  const clicksBeforeReview = calls.length;
  const likeReview = await run('click','Like this video');
  assert.match(likeReview.confirm,/191,712/);
  assert.doesNotMatch(likeReview.confirm,/comment/);
  assert.equal(calls.length,clicksBeforeReview);
  assert.equal((await run('approve',likeReview.ticket)).detail,'Liked the video.');
  assert.equal(calls.at(-1)[0],'like');
  const clicksAfterLike = calls.length;
  const already = await run('click','Like this video');
  assert.equal(already.detail,'This video is already liked.');
  assert.ok(!already.confirm);
  assert.equal(calls.length,clicksAfterLike);
  extraItems[0].pressed = null;
  await assert.rejects(run('click','Like this video'),/already liked/);
  extraItems.push({...extraItems[0],pressed:'false'});
  await assert.rejects(run('click','Like this video'),/one Like button/);
  extraItems = extraItems.slice(1,3);
  await assert.rejects(run('click','Like this video'),/one Like button/);
  url = 'https://fixture.test/';
  await assert.rejects(run('click','Like this video'),/Open the YouTube video itself/);
  extraItems = [{role:'button',name:'Like',type:'',href:'',pressed:'false'}, {role:'field',name:'Like field',type:'text',href:''}];
  const genericLike = await run('click','Like');
  assert.match(genericLike.confirm,/click/);
  const genericFill = await run('fill',JSON.stringify({field:'Like field',value:'hello'}));
  assert.match(genericFill.confirm,/fill/);
  let pairingReply;
  listeners.message({type:'pair',token:'1'.repeat(64)},{tab:{url:'https://evil.test/connect#'+'1'.repeat(64)}},v=>pairingReply=v);
  assert.match(pairingReply.error,/Open the connection page/);
  console.log('PASS: extension reviews, single-use approvals, page/tab changes, fields, links, pairing origin and allowlist.');
})().catch(error=>{console.error(error);process.exitCode=1;});
