import {useEffect,useState} from 'react';
import {Trash2,RotateCcw,AlertCircle} from 'lucide-react';
import {api,post} from './api';
import {Modal,Table,Loading} from './components';
import type {Case} from './types';

export function CaseDeleteButton({caseData:c,onDeleted}:{caseData:Case;onDeleted:()=>Promise<void>}){
 const [open,setOpen]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 return <><button className="icon-btn case-delete" type="button" title="Hapus perkara" aria-label={'Hapus perkara '+c.number} onClick={()=>{setError('');setOpen(true)}}><Trash2 size={17}/></button>{open&&<Modal title="Hapus perkara?" close={()=>{if(!busy)setOpen(false)}}><div className="modal-body"><strong>{c.number}</strong><p>Perkara dan BAP dipindahkan ke Terhapus. Bisa dipulihkan kembali.</p>{error&&<div className="alert error" role="alert">{error}</div>}<div className="form-actions"><button className="btn secondary" disabled={busy} onClick={()=>setOpen(false)}>Batal</button><button className="btn primary" disabled={busy} onClick={async()=>{setBusy(true);try{await api('/cases/'+c.id+'?expected_revision='+c.revision,{method:'DELETE'});setOpen(false);await onDeleted()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}><Trash2 size={16}/>{busy?'Menghapus…':'Hapus'}</button></div></div></Modal>}</>;
}

export function DeletedCases({onRestored}:{onRestored:()=>Promise<void>}){
 const [cases,setCases]=useState<Case[]>([]),[loaded,setLoaded]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState('');
 const load=async()=>{try{setCases(await api<Case[]>('/cases?deleted=true'));setLoaded(true)}catch(e){setError((e as Error).message);setLoaded(true)}};
 useEffect(()=>{load()},[]);
 return <section className="panel">{error&&<div className="alert error" role="alert"><AlertCircle size={17}/>{error}</div>}{!loaded?<Loading/>:<Table items={cases} searchText={c=>c.number+' '+c.document.name} emptyTitle="Tidak ada perkara terhapus" columns={[{title:'Perkara',render:c=><div className="stacked"><strong>{c.number}</strong><small>{c.document.name}</small></div>},{title:'Pihak terkait',render:c=>c.persons.map(person=>String(person.name||'')).filter(Boolean).join(', ')||'—'},{title:'Tindakan',render:c=><button className="btn secondary" disabled={!!busy} onClick={async()=>{setBusy(c.id);setError('');try{await post('/cases/'+c.id+'/restore');await load();await onRestored()}catch(e){setError((e as Error).message)}finally{setBusy('')}}}><RotateCcw size={16}/>{busy===c.id?'Memulihkan…':'Pulihkan'}</button>}]}/>}</section>;
}
