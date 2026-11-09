/* Real HTTP + packaged service-worker code; only Chrome's UI/DOM APIs are fixtures. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),readline=require('node:readline');
const {webcrypto}=require('node:crypto');
const folder=path.join(__dirname,'..','chrome-extension');
const origin='chrome-extension://'+'a'.repeat(32);
let context,listeners={},pools={local:{},session:{}},url='https://fixture.test/video',calls=[],alarms=0,resultRequests=0,dropAck=false;
let holdPollError=false,releasePollError=null;
const out=value=>process.stdout.write(JSON.stringify(value)+'\n');
const storage=pool=>({get:async key=>({[key]:pool[key]}),set:async v=>Object.assign(pool,v),remove:async key=>delete pool[key]});
function start(message){
  pools.local.pairing={token:message.token};
  const current=()=>({id:1,url,status:'complete',windowId:1,title:'Fixture video'});
  const sandbox={URL,AbortSignal,crypto:webcrypto,setTimeout,clearTimeout,console,fetch:async(value,options)=>{
    if(value.endsWith('/result'))resultRequests++;
    const response=await fetch(value,{...options,headers:{...options.headers,Origin:origin}});
    if(value.endsWith('/poll')&&response.status===403&&holdPollError){holdPollError=false;out({event:'poll_held'});await new Promise(resolve=>releasePollError=resolve);}
    if(value.endsWith('/result')&&dropAck){dropAck=false;await response.arrayBuffer();throw TypeError('Simulated lost acknowledgement');}
    return response;
  },chrome:{
    storage:{local:storage(pools.local),session:storage(pools.session)},
    runtime:{getManifest:()=>({version:'1.2.0'}),getURL:p=>origin+'/'+p,
      onMessage:{addListener:fn=>listeners.message=fn},onStartup:{addListener:fn=>listeners.startup=fn},onInstalled:{addListener:fn=>listeners.installed=fn}},
    alarms:{get:async()=>null,create:async()=>{alarms++;},onAlarm:{addListener:fn=>listeners.alarm=fn}},
    windows:{update:async()=>{}},
    tabs:{query:async()=>[current()],get:async()=>current(),create:async o=>{url=o.url;return current();},
      update:async()=>current(),remove:async()=>{url='https://fixture.test/video';},goBack:async()=>{},goForward:async()=>{},reload:async()=>{}},
    scripting:{executeScript:async({files,args})=>{
      if(files)return[];
      const [name,values]=args;
      if(name==='observePage')return[{result:{ok:true,value:{url,title:'Fixture video',items:[],text:'Fixture'}}}];
      calls.push({operation:values[0],url});
      return[{result:{ok:true,value:{paused:true,muted:false}}}];
    }}
  }};
  context=vm.createContext(sandbox);
  sandbox.importScripts=file=>vm.runInContext(fs.readFileSync(path.join(folder,file),'utf8'),context);
  const source=fs.readFileSync(path.join(folder,'background.js'),'utf8').replace("const BASE = 'http://127.0.0.1:17653';",'const BASE = '+JSON.stringify(message.base)+';');
  vm.runInContext(source,context);
  out({event:'started'});
}
readline.createInterface({input:process.stdin}).on('line',line=>{
  try{
    const m=JSON.parse(line);
    if(m.type==='start')return start(m);
    if(m.type==='quit')process.exit(0);
    if(m.type==='status')return out({event:'status',calls,alarms,resultRequests,polling:vm.runInContext('polling',context)});
    if(m.type==='drop_ack'){dropAck=true;return out({event:'armed'});}
    if(m.type==='hold_poll_error'){holdPollError=true;return out({event:'armed'});}
    if(m.type==='release_poll'){releasePollError?.();releasePollError=null;return;}
    if(m.type==='pair'){
      url=m.base+'/connect#'+m.code;
      listeners.message({type:'pair',token:m.code},{tab:{id:1,url}},r=>{url='https://fixture.test/video';out({event:'paired',ok:r.ok,error:r.error});});
    }
    if(m.type==='wake'){
      url=m.url;
      listeners.message({type:'wake',id:new URL(m.url).hash.slice(1)},{tab:{id:1,url}},r=>out({event:'wake',ok:r.ok,error:r.error}));
    }
  }catch(error){out({event:'error',error:String(error)});}
});
