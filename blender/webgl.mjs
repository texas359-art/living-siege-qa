import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
const root=process.cwd(),out=path.join(root,'model-results');
const html=`<!doctype html><html><head><style>html,body{margin:0;background:#15212d}canvas{display:block}</style><script type="importmap">{"imports":{"three":"/node_modules/three/build/three.module.js","three/addons/":"/node_modules/three/examples/jsm/"}}</script></head><body><canvas></canvas><script type="module">
import * as T from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const renderer=new T.WebGLRenderer({canvas:document.querySelector('canvas'),antialias:true});renderer.setSize(720,720);renderer.setPixelRatio(1);renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;
const scene=new T.Scene();scene.background=new T.Color('#15212d');const camera=new T.PerspectiveCamera(32,1,.1,40);scene.add(new T.HemisphereLight('#c5e6ff','#252522',2.0));
const key=new T.DirectionalLight('#ffdab5',4);key.position.set(-4,7,5);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-4;key.shadow.camera.right=4;key.shadow.camera.top=4;key.shadow.camera.bottom=-4;key.shadow.normalBias=.025;scene.add(key);
const rim=new T.DirectionalLight('#8ac9ff',2);rim.position.set(3,5,-4);scene.add(rim);
const ground=new T.Mesh(new T.PlaneGeometry(40,40),new T.MeshStandardMaterial({color:'#334351',roughness:.9}));ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);
let model,mixer,gltf,current,previous=performance.now();
function render(){renderer.render(scene,camera)}
function pixels(){const gl=renderer.getContext(),w=gl.drawingBufferWidth,h=gl.drawingBufferHeight,a=new Uint8Array(w*h*4),b=new Uint8Array(w*h*4);render();gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,a);model.visible=false;render();gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,b);model.visible=true;render();let count=0;for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>12)count++;return{actorPixels:count,error:gl.getError()}}
window.__modelQA={async load(name){if(model)scene.remove(model);gltf=await new GLTFLoader().loadAsync('/model-results/'+name+'.glb');model=gltf.scene;model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true}});scene.add(model);mixer=new T.AnimationMixer(model);return{clips:gltf.animations.map(a=>({name:a.name,duration:a.duration,tracks:a.tracks.length})),bones:Math.max(...[...function*(){let a=[];model.traverse(o=>{if(o.isSkinnedMesh)a.push(o.skeleton.bones.length)});yield* a}()]),textures:[...new Set(function(){let a=[];model.traverse(o=>{if(o.isMesh)for(const m of(Array.isArray(o.material)?o.material:[o.material]))if(m.map)a.push(m.map)});return a}())].map(t=>({width:t.image.width,height:t.image.height}))}},pose(view,state='Idle',time=0){mixer.stopAllAction();let clip=gltf.animations.find(a=>a.name===state);if(!clip)throw Error('Missing '+state);current=mixer.clipAction(clip);current.play();current.paused=true;current.time=time;mixer.update(0);const views={front:[0,1.5,7],side:[7,1.5,0],game:[-4,4.8,6]};camera.position.fromArray(views[view]);camera.lookAt(-.12,1.45,0);render();return pixels()},joints(){const names=['footl','footr','handl','handr','spine'];return Object.fromEntries(names.map(n=>{const b=model.getObjectByName(n);return[n,b?.quaternion.toArray()]}))},pixels};
function draw(now){previous=now;render();requestAnimationFrame(draw)}requestAnimationFrame(draw);
</script></body></html>`;
const server=http.createServer(async(req,res)=>{try{const url=new URL(req.url,'http://localhost');if(url.pathname==='/'){res.setHeader('Content-Type','text/html');res.end(html);return}const file=path.resolve(root,'.'+decodeURIComponent(url.pathname));if(!file.startsWith(root+path.sep))throw Error('outside root');const data=await fs.readFile(file);res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.glb')?'model/gltf-binary':'application/octet-stream');res.end(data)}catch{res.statusCode=404;res.end()}});
await new Promise(resolve=>server.listen(4173,'127.0.0.1',resolve));let browser;const report={result:'NOT_RUN',errors:[],variants:[],physicalIphone:false};
try{
 const disabled=['AcceptCHFrame','AvoidUnnecessaryBeforeUnloadCheckSync','DestroyProfileOnBrowserClose','DialMediaRouteProvider','GlobalMediaControls','HttpsUpgrades','LensOverlay','MediaRouter','PaintHolding','ThirdPartyStoragePartitioning','Translate','AutoDeElevate'];
 browser=await chromium.launch({channel:'chromium',headless:true,chromiumSandbox:true,args:['--use-gl=angle','--use-angle=swiftshader'],ignoreDefaultArgs:['--enable-unsafe-swiftshader','--disable-client-side-phishing-detection','--disable-ipc-flooding-protection','--unsafely-disable-devtools-self-xss-warnings','--disable-popup-blocking','--disable-component-update','--disable-features='+disabled.join(',')]});
 const session=await browser.newBrowserCDPSession();report.arguments=(await session.send('Browser.getBrowserCommandLine')).arguments;
 for(const flag of ['--no-sandbox','--disable-web-security','--enable-unsafe-swiftshader','--ignore-certificate-errors'])assert(!report.arguments.includes(flag));
 const page=await browser.newPage({viewport:{width:720,height:720},deviceScaleFactor:1});page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto('http://127.0.0.1:4173');await page.waitForFunction(()=>window.__modelQA);
 for(const name of ['tower','forge','sentinel','raider']){
  const data=await page.evaluate(n=>window.__modelQA.load(n),name);assert(data.bones>=15);assert(data.textures.length>0);assert(data.clips.length>=5);report.variants.push({name,...data});
  if(name!=='raider')for(const view of ['front','side','game']){const px=await page.evaluate(v=>window.__modelQA.pose(v),view);assert(px.actorPixels>1000);assert.equal(px.error,0);await page.locator('canvas').screenshot({path:path.join(out,name+'-webgl-'+view+'.png')});}
  for(const [state,time]of [['Idle',.5],['Walk',.25],['Attack',13/30],['Hit',.18],['Death',1.5]]){
   const px=await page.evaluate(({state,time})=>window.__modelQA.pose('game',state,time),{state,time});assert(px.actorPixels>500);assert.equal(px.error,0);
   if(name==='tower')await page.locator('canvas').screenshot({path:path.join(out,'tower-'+state+'.png')});
  }
  await page.evaluate(()=>window.__modelQA.pose('game','Walk',.1));const before=await page.evaluate(()=>window.__modelQA.joints());await page.evaluate(()=>window.__modelQA.pose('game','Walk',.5));const after=await page.evaluate(()=>window.__modelQA.joints());for(const j of ['footl','footr','handl','handr'])if(JSON.stringify(before[j])===JSON.stringify(after[j]))report.errors.push(name+': Walk joint unchanged '+j);
 }
 assert.equal(report.errors.length,0);report.result='PASS';
}catch(e){report.result='FAIL';report.errors.push(e.stack);process.exitCode=1}finally{await browser?.close();server.close();await fs.writeFile(path.join(out,'webgl-report.json'),JSON.stringify(report,null,2))}
