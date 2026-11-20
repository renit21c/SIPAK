import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';

const publicUrl=new URL('../../public/',import.meta.url);
function worker(){
 const events={},added=[],deleted=[];
 const context={URL,Response,fetch:async()=>{throw new TypeError('offline')},caches:{open:async()=>({add:async path=>{added.push(path)}}),keys:async()=>['sipak-offline-v1','sipak-offline-v2','another-app-cache'],delete:async key=>{deleted.push(key)},match:async path=>path==='/offline.html'?new Response('SIPAK offline page'):undefined},self:{location:{origin:'https://sipak.test'},addEventListener:(name,callback)=>{events[name]=callback},skipWaiting:async()=>{},clients:{claim:async()=>{}}}};
 vm.runInNewContext(readFileSync(new URL('sw.js',publicUrl),'utf8'),context);
 return {events,added,deleted};
}

test('manifest is linked and icon dimensions match their declarations',()=>{
 const manifest=JSON.parse(readFileSync(new URL('manifest.webmanifest',publicUrl),'utf8'));
 const html=readFileSync(new URL('../../index.html',import.meta.url),'utf8');
 assert.match(html,/rel="manifest" href="\/manifest.webmanifest"/);
 assert.equal(manifest.display,'standalone');assert.equal(manifest.scope,'/');
 assert.equal(manifest.start_url,'/');assert.equal(manifest.name,'SIPAK');assert.equal(manifest.short_name,'SIPAK');assert.match(html,/<title>SIPAK<\/title>/);
 for(const icon of manifest.icons){
  const path=new URL(icon.src.slice(1),publicUrl);assert.ok(existsSync(fileURLToPath(path)));
  const png=readFileSync(path);assert.equal(png.toString('ascii',1,4),'PNG');
  assert.equal(`${png.readUInt32BE(16)}x${png.readUInt32BE(20)}`,icon.sizes);
 }
 assert.ok(manifest.icons.some(icon=>icon.purpose==='maskable'));
 for(const path of ['favicon.ico','favicon.svg','apple-touch-icon.png'])assert.ok(existsSync(new URL(path,publicUrl)));
});

test('worker only precaches the public offline page and cleans its own old cache',async()=>{
 const {events,added,deleted}=worker();let pending;
 events.install({waitUntil:promise=>{pending=promise}});await pending;
 assert.deepEqual(added,['/offline.html']);
 events.activate({waitUntil:promise=>{pending=promise}});await pending;
 assert.deepEqual(deleted,['sipak-offline-v1']);
});

test('API, BAP, recommendation PDFs, writes and external resources bypass the worker',()=>{
 const {events}=worker();let intercepted=0;
 for(const [path,method,mode] of [['/api/cases','GET','navigate'],['/api/documents/test/pdf','GET','navigate'],['/api/cases/test/recommendation','GET','navigate'],['/api/attachments/test/pdf','GET','navigate'],['/','POST','navigate'],['/icons/sipak-192.png','GET','no-cors'],['https://external.test/','GET','navigate']]){
  events.fetch({request:{url:new URL(path,'https://sipak.test').href,method,mode},respondWith:()=>{intercepted++}});
 }
 assert.equal(intercepted,0);
});

test('offline navigation returns the fallback instead of a cached authenticated page',async()=>{
 const {events}=worker();let pending;
 events.fetch({request:{url:'https://sipak.test/',method:'GET',mode:'navigate'},respondWith:promise=>{pending=promise}});
 const response=await pending;assert.equal(await response.text(),'SIPAK offline page');
});
