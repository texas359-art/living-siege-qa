import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

// This launches a NEW, disposable browser. Never connects to a user browser.
const target=process.env.BASTION_URL||'https://living-siege.starmedved.chatgpt.site/bastion-test?v=6';
const output=path.resolve(process.env.BASTION_QA_OUTPUT||'bastion-qa-results');
await fs.mkdir(output,{recursive:true});
const report={url:target,started:new Date().toISOString(),result:'NOT_RUN',security:{chromiumSandbox:true,bypassCSP:false,ignoreHTTPSErrors:false,unsafeSwiftShader:false},screenshots:[],tests:[],errors:[],physicalIphoneTest:'NOT_PERFORMED: mobile viewport is not a physical iPhone'};
let browser,context,page;
try{
 const location=process.env.BASTION_PLAYWRIGHT_PATH;
 const {chromium}=await import(location?pathToFileURL(location).href:'playwright');
 // Match the proven reference's Playwright version, retaining browser protections.
 const disabledFeatures=['AcceptCHFrame','AvoidUnnecessaryBeforeUnloadCheckSync','DestroyProfileOnBrowserClose','DialMediaRouteProvider','GlobalMediaControls','HttpsUpgrades','LensOverlay','MediaRouter','PaintHolding','ThirdPartyStoragePartitioning','Translate','AutoDeElevate'];
 browser=await chromium.launch({channel:'chromium',headless:true,chromiumSandbox:true,args:['--use-gl=angle','--use-angle=swiftshader'],ignoreDefaultArgs:['--enable-unsafe-swiftshader','--disable-client-side-phishing-detection','--disable-ipc-flooding-protection','--unsafely-disable-devtools-self-xss-warnings','--disable-popup-blocking','--disable-component-update',`--disable-features=${disabledFeatures.join(',')}`]});
 report.browser=browser.version();
 const session=await browser.newBrowserCDPSession();const command=await session.send('Browser.getBrowserCommandLine');report.security.actualArguments=command.arguments;await session.detach();
 for(const flag of ['--no-sandbox','--disable-setuid-sandbox','--disable-web-security','--enable-unsafe-swiftshader','--disable-webgl','--ignore-certificate-errors','--disable-ipc-flooding-protection','--disable-client-side-phishing-detection'])assert(!command.arguments.some(a=>a===flag||a.startsWith(flag+'=')),`Forbidden browser flag: ${flag}`);
 assert(!command.arguments.some(a=>a.startsWith('--disable-features=')),'Unexpected disabled browser features');
 context=await browser.newContext({viewport:{width:1100,height:900},deviceScaleFactor:1,recordVideo:{dir:path.join(output,'videos'),size:{width:1100,height:900}},bypassCSP:false,ignoreHTTPSErrors:false});
 page=await context.newPage();
 await page.route('**/*',route=>{const url=new URL(route.request().url());return ['blob:','data:'].includes(url.protocol)||url.origin===new URL(target).origin?route.continue():route.abort('blockedbyclient');});
 const pageErrors=[];page.on('pageerror',error=>pageErrors.push(error.message));page.on('console',message=>{if(message.type()==='error')pageErrors.push(message.text());});
 const failedRequests=[];page.on('requestfailed',request=>failedRequests.push({url:request.url(),failure:request.failure()?.errorText}));
 const badResponses=[];page.on('response',response=>{if(response.status()>=400)badResponses.push({url:response.url(),status:response.status()});});
 const probe=await page.evaluate(()=>{const canvas=document.createElement('canvas'),gl=canvas.getContext('webgl2');if(!gl)return{webgl2:false};const debug=gl.getExtension('WEBGL_debug_renderer_info');const result={webgl2:true,version:gl.getParameter(gl.VERSION),renderer:gl.getParameter(debug?debug.UNMASKED_RENDERER_WEBGL:gl.RENDERER)};gl.getExtension('WEBGL_lose_context')?.loseContext();return result;});
 report.contextProbe=probe;assert(probe.webgl2,'WebGL2 unavailable. Do NOT retry with security-disabling flags.');assert(/swiftshader/i.test(probe.renderer),'SwiftShader renderer was requested but not actually selected.');
 const response=await page.goto(target,{waitUntil:'load',timeout:60000});assert.equal(response.status(),200);
 await page.waitForFunction(()=>Boolean(window.__bastionTest),{},{timeout:60000});
 const inspect=()=>page.evaluate(()=>window.__bastionTest.inspect());
 const start=await inspect();assert(start.webgl2);assert.equal(start.bones,41);assert(start.textures.length>0);assert(start.textures.every(t=>t.width>0&&t.height>0));
 for(const clip of ['Idle','Walking_A','Block_Attack','Hit_A','Death_A'])assert(start.clips.some(c=>c.name===clip&&c.tracks>0));
 report.assets={bones:start.bones,textures:start.textures,clips:start.clips};report.tests.push('WebGL2 + SwiftShader','GLB and embedded texture decoded','skeletal animation clips present');
 const canvas=page.locator('.bastion-stage canvas');
 const checksums=[];
 for(const [state,label,time] of [['idle','Idle',.5],['walk','Walk',.3],['attack','Attack',.48],['hit','Hit',.28],['death','Death',.79]]){
  await page.getByRole('button',{name:label,exact:true}).click();
  await page.evaluate(({state,time})=>window.__bastionTest.previewAt(state,time),{state,time});
  await page.waitForFunction(state=>window.__bastionTest.inspect().actors[0].state===state,state);
  // Allow cross-fades to finish. This is not replacing the scene with an image.
  await page.waitForTimeout(250);
  const pixels=await page.evaluate(()=>window.__bastionTest.pixels());assert.equal(pixels.glError,0);assert(pixels.actorPixels>100,`${label}: no actual model pixels rendered`);checksums.push(pixels.checksum);
  const filename=`${label}.png`;await canvas.screenshot({path:path.join(output,filename)});report.screenshots.push({state,file:filename,pixels});
 }
 assert(new Set(checksums).size>=4,'Animation states rendered identical images');
 await page.getByRole('button',{name:'Walk',exact:true}).click();const before=await inspect();await page.waitForTimeout(400);const after=await inspect();
 for(const joint of ['footl','footr','handl','handr'])assert.notDeepEqual(before.actors[0].joints[joint],after.actors[0].joints[joint],`Walk bone does not animate: ${joint}`);
 report.tests.push('five real canvas screenshots + model/background pixel difference','independent foot/hand animation');
 // Orbit and zoom exercise the actual camera, not a CSS transform.
 const box=await canvas.boundingBox();const cameraBefore=(await inspect()).camera;
 await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+130,box.y+box.height/2+30,{steps:10});await page.mouse.up();await page.waitForTimeout(300);
 assert.notDeepEqual((await inspect()).camera,cameraBefore);await page.mouse.wheel(0,-180);await page.waitForTimeout(250);await page.getByRole('button',{name:'Сбросить камеру'}).click();report.tests.push('camera rotation and zoom');
 await page.getByRole('button',{name:'Бастион против Бастиона',exact:true}).click();
 await canvas.scrollIntoViewIfNeeded();report.fightCanvas=await canvas.boundingBox();
 const seen=new Set();let damaged=false,died=false,previousHp=[250,250],last;
 const fightStart=Date.now();
 while(Date.now()-fightStart<240000){
  last=await inspect();for(let i=0;i<last.actors.length;i++){const actor=last.actors[i];seen.add(actor.state);if(actor.hp!==null&&actor.hp<previousHp[i])damaged=true;if(actor.hp!==null)previousHp[i]=actor.hp;if(actor.state==='death')died=true;}
  if(last.finished)break;await page.waitForTimeout(100);
 }
 assert(last.finished,'Real-time battle did not finish in 240s');assert(seen.has('walk'));assert(seen.has('attack'));assert(damaged);assert(died);assert(last.frames>0);assert.equal(last.errors.length,0);
 report.duel={seconds:last.elapsed,wallSeconds:(Date.now()-fightStart)/1000,seenStates:[...seen],damageObserved:damaged,deathObserved:died,finished:last.finished,softwareFps:last.fps};
 await page.screenshot({path:path.join(output,'desktop-diagnostics.png'),fullPage:true});
 // Responsive QA only. Explicitly NOT Safari/iPhone performance certification.
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Idle',exact:true}).click();await page.waitForTimeout(300);
 const mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,buttons:[...document.querySelectorAll('nav button')].map(b=>({height:b.getBoundingClientRect().height,width:b.getBoundingClientRect().width})),diagnostics:document.querySelector('[data-testid="diagnostics"]')?.textContent}));
 assert(mobile.scrollWidth<=mobile.width);assert(mobile.buttons.every(b=>b.height>=44));assert(mobile.diagnostics.includes('WebGL 2'));await page.screenshot({path:path.join(output,'mobile-viewport.png'),fullPage:true});report.mobileViewport=mobile;
 assert.equal(pageErrors.length,0,JSON.stringify(pageErrors));assert.equal(failedRequests.length,0,JSON.stringify(failedRequests));assert.equal(badResponses.length,0,JSON.stringify(badResponses));report.tests.push('real-time duel: movement, attacks, HP decrease, death, finish','390×844 responsive layout','no JS / rendering / network errors');
 report.result='PASS';
 const video=page.video();await context.close();context=null;await video.saveAs(path.join(output,'bastion-session.webm'));report.video='bastion-session.webm';
}catch(error){report.result='FAIL';report.errors.push(error.stack||String(error));if(page&&!page.isClosed())await page.screenshot({path:path.join(output,'failure-page.png'),fullPage:true}).catch(()=>{});process.exitCode=1;}
finally{if(context){const video=page?.video();await context.close().catch(()=>{});if(video)await video.saveAs(path.join(output,'failed-session.webm')).catch(()=>{});}await browser?.close();report.finished=new Date().toISOString();await fs.writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));}
