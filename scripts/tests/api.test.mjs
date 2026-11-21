import {readFile} from 'node:fs/promises';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

const source=await readFile(new URL('../../src/api.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {api}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const json=(detail,status)=>new Response(JSON.stringify({detail}),{status,headers:{'Content-Type':'application/json'}});

test('old backend feature routes explain that the server needs a restart',async t=>{
 t.mock.method(globalThis,'fetch',async()=>json('Not Found',404));
 for(const path of ['/settings/letterhead','/evaluation/articles','/cases/test/evaluation/draft'])await assert.rejects(api(path),/Muat ulang server SIPAK/);
});
test('case errors preserve the useful backend message',async t=>{
 t.mock.method(globalThis,'fetch',async()=>json('Perkara tidak ditemukan.',404));
 await assert.rejects(api('/cases/test'),/Perkara tidak ditemukan/);
});
test('HTML gateway errors are distinguished from network failures',async t=>{
 t.mock.method(globalThis,'fetch',async()=>new Response('<html>private proxy diagnostic</html>',{status:502}));
 await assert.rejects(api('/settings/letterhead'),/Server SIPAK belum tersedia/);
 t.mock.method(globalThis,'fetch',async()=>{throw new TypeError('fetch failed')});
 await assert.rejects(api('/settings/letterhead'),/Koneksi ke server SIPAK terputus/);
});
test('validation errors show messages without echoing submitted inputs',async t=>{
 t.mock.method(globalThis,'fetch',async()=>json([{msg:'Isian tidak valid.',input:'private-value'}],422));
 await assert.rejects(api('/settings/letterhead'),error=>error.message==='Isian tidak valid.');
});
test('success uses the same origin session and malformed success is reported',async t=>{
 t.mock.method(globalThis,'fetch',async(url,options)=>{assert.equal(url,'/api/settings/letterhead');assert.equal(options.credentials,'same-origin');return Response.json({unit_name:'KOMISI DISIPLIN'})});
 assert.deepEqual(await api('/settings/letterhead'),{unit_name:'KOMISI DISIPLIN'});
 t.mock.method(globalThis,'fetch',async()=>new Response('<html>stale frontend</html>'));
 await assert.rejects(api('/settings/letterhead'),/Respons server SIPAK tidak valid/);
});
