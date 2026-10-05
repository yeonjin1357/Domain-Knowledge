// Headless Chrome DevTools verification. Node 22+, no npm dependencies.
import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const expectedDiagrams=(await readFile(path.join(root,'BOOK.md'),'utf8')).match(/^```mermaid\s*$/gm)?.length||0;
const browser=process.argv[2]||'C:/Program Files/Google/Chrome/Application/chrome.exe';
const cache=path.join(root,'.lab-runs','html-review');
await mkdir(cache,{recursive:true});
const profile=path.join(cache,`cdp-${Date.now()}`);
const child=spawn(browser,['--headless=new','--no-first-run','--disable-extensions','--disable-sync',
  '--disable-background-networking','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1',
  `--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore',windowsHide:true});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const assert=(test,message)=>{if(!test)throw new Error(message)};
let socket;
let nextId=0;
const pending=new Map();
function call(method,params={},sessionId){
  const id=++nextId;
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{pending.delete(id);reject(new Error(`Timeout: ${method}`))},20000);
    pending.set(id,{resolve,reject,timer});
    socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));
  });
}
try{
  const portFile=path.join(profile,'DevToolsActivePort');
  for(let i=0;i<150&&!existsSync(portFile);i++)await delay(100);
  assert(existsSync(portFile),'Chrome did not create its isolated debugging endpoint');
  const [port,endpoint]=(await readFile(portFile,'utf8')).trim().split(/\r?\n/);
  socket=new WebSocket(`ws://127.0.0.1:${port}${endpoint}`);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject});
  socket.onmessage=event=>{
    const reply=JSON.parse(event.data);const item=pending.get(reply.id);
    if(item){clearTimeout(item.timer);pending.delete(reply.id);reply.error?item.reject(new Error(JSON.stringify(reply.error))):item.resolve(reply.result)}
  };
  const version=await call('Browser.getVersion');
  const result={checked_at_utc:new Date().toISOString(),browser:version.product,node:process.version,
    book_html_sha256:createHash('sha256').update(await readFile(path.join(root,'BOOK.html'))).digest('hex'),
    network_mode:'offline via Network.emulateNetworkConditions',expected_diagrams:expectedDiagrams,pages:{}};
  const cases=[['desktop',1440,1000,''],['chapter',1440,1000,'chapter-docs-host-cpu'],
    ['diagram',1440,1000,'chapter-docs-database-transactions-and-locks--잠금-대기와-교착-상태'],
    ['mobile',390,844,'chapter-docs-foundations-system-map'],
    ['new-diagram',1440,1000,'chapter-docs-database-postgresql-concurrency-lab--실습-3-active인데-cpu를-실행하고-있지-않다'],
    ['mobile-contract',390,844,'chapter-docs-product-compatibility-and-acceptance--linux-필드의-구체적인-계약']];
  for(const [name,width,height,fragment] of cases){
    const {targetId}=await call('Target.createTarget',{url:'about:blank'});
    const {sessionId}=await call('Target.attachToTarget',{targetId,flatten:true});
    const send=(m,p)=>call(m,p,sessionId);
    await send('Page.enable');
    await send('Runtime.enable');
    await send('Network.enable');
    await send('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name.startsWith('mobile')});
    await send('Page.navigate',{url:pathToFileURL(path.join(root,'BOOK.html')).href+(fragment?'#'+encodeURIComponent(fragment):'')});
    let ready=false;
    for(let i=0;i<200;i++){
      const v=await send('Runtime.evaluate',{expression:"document.documentElement.dataset.bookReady==='true'",returnByValue:true});
      if(v.result?.value){ready=true;break}await delay(100);
    }
    assert(ready,`${name}: book did not finish rendering`);
    if(fragment)await send('Runtime.evaluate',{expression:`document.getElementById(${JSON.stringify(fragment)}).scrollIntoView()`});
    await send('Page.bringToFront');
    await send('Runtime.evaluate',{expression:'new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(true))))',awaitPromise:true,returnByValue:true});
    await delay(150);
    const facts=await send('Runtime.evaluate',{expression:`(()=>{const target=document.getElementById(${JSON.stringify(fragment||'book-top')});return {
      width:innerWidth,height:innerHeight,document_width:document.documentElement.scrollWidth,
      diagrams:document.querySelectorAll('.mermaid svg').length,errors:window.__bookErrors,
      missing_anchors:[...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).length,
      external_scripts:document.querySelectorAll('script[src]').length,
      target_exists:!!target,target_top:target?.getBoundingClientRect().top,
      body_text_length:document.querySelector('main').innerText.length,
      visible_heading:[...document.querySelectorAll('main h2, main h3')].find(h=>h.getBoundingClientRect().top>=0&&h.getBoundingClientRect().top<innerHeight)?.textContent
    }})()`,returnByValue:true});
    const f=facts.result.value;
    assert(f.width===width,`${name}: viewport ${f.width} != ${width}`);
    assert(f.document_width<=width,`${name}: page overflows horizontally`);
    assert(expectedDiagrams>0&&f.diagrams===expectedDiagrams&&f.errors.length===0,`${name}: diagram rendering failed`);
    assert(f.missing_anchors===0&&f.target_exists,`${name}: broken navigation`);
    assert(f.external_scripts===0&&f.body_text_length>100000,`${name}: incomplete document`);
    assert(f.visible_heading,`${name}: no visible chapter heading after navigation`);
    // Exercise title search in the actual page, then reset before the screenshot.
    const search=await send('Runtime.evaluate',{expression:`(()=>{const i=document.getElementById('toc-search');i.value='CPU';i.dispatchEvent(new Event('input'));const list=[...document.querySelectorAll('nav li')].filter(x=>!x.hidden);const ok=list.length>0&&list.every(x=>x.textContent.toLowerCase().includes('cpu'));i.value='';i.dispatchEvent(new Event('input'));return ok})()`,returnByValue:true});
    assert(search.result.value,`${name}: TOC search failed`);
    if(name.startsWith('mobile'))await send('Runtime.evaluate',{expression:"document.querySelector('aside').classList.remove('open');document.activeElement?.blur()"});
    const screenshot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true});
    await writeFile(path.join(cache,`${name}.png`),Buffer.from(screenshot.data,'base64'));
    result.pages[name]={...f,title_search_passed:true,fragment};
    process.stdout.write(`${name}: ${width}x${height}, diagrams=${f.diagrams}, heading=${f.visible_heading}\n`);
    await call('Target.closeTarget',{targetId});
  }
  await writeFile(path.join(root,'review/html-check.json'),JSON.stringify(result,null,2)+'\n');
  process.stdout.write(`PASS: offline browser rendering, ${cases.length} viewports/locations, TOC search, ${expectedDiagrams} diagrams, anchors\n`);
  await call('Browser.close');
}finally{
  if(socket)socket.close();
  for(const item of pending.values())clearTimeout(item.timer);
  child.kill();
}
