import {useState} from 'react';
import {Gavel,ClipboardCheck,FileDown,Eye,FolderOpen} from 'lucide-react';
import {Badge,Table,Select} from '../components';
import {date,text,type Case,type User} from '../types';
import {CasesPage} from './Cases';

export function VerificationPage({cases,user,go}:{cases:Case[];user:User;go:(route:string)=>void}){
 return <CasesPage cases={cases.filter(c=>!c.verified)} user={user} go={go} mode="verification"/>;
}

export function DecisionsPage({cases,go}:{cases:Case[];go:(route:string)=>void}){
 const [filter,setFilter]=useState('pending');
 const pending=cases.filter(c=>c.status==='Menunggu Keputusan Berwenang');
 const issued=cases.filter(c=>c.status==='Keputusan Resmi Diterbitkan');
 return <><div className="decision-summary"><div><Gavel size={25}/><strong>{pending.length}</strong><span>Menunggu keputusan</span></div><div><ClipboardCheck size={25}/><strong>{issued.length}</strong><span>Keputusan tercatat</span></div></div><section className="panel"><header className="panel-heading"><h2>{filter==='pending'?'Siap Ditinjau':'Keputusan Tercatat'}</h2><Select label="Status keputusan" value={filter} onChange={setFilter}><option value="pending">Menunggu keputusan</option><option value="issued">Keputusan tercatat</option></Select></header><Table items={filter==='pending'?pending:issued} searchText={c=>c.number+' '+c.persons.map(p=>p.name).join(' ')} columns={[{title:'Perkara',render:c=><strong>{c.number}</strong>},{title:'Pihak Terkait',render:c=>c.persons.map(p=>text(p.name)).join(', ')||'—'},{title:'Penilaian Awal',render:c=>c.analysis.filter(a=>a.sanction).map(a=>a.sanction).join('; ')||'Belum dinilai'},{title:'Status',render:c=><Badge>{c.status}</Badge>},{title:'',render:c=><button className="icon-action" aria-label={'Tinjau '+c.number} title="Tinjau pemeriksaan dan keputusan" onClick={()=>go('case/'+c.id+'?tab=workflow')}><Eye size={18}/></button>}]} emptyTitle={filter==='pending'?'Belum ada perkara siap diputuskan':'Belum ada keputusan tercatat'}/></section></>;
}

export function ReportsPage({cases,go}:{cases:Case[];go:(route:string)=>void}){
 return <section className="panel"><header className="panel-heading"><h2>Laporan Perkara</h2><FileDown size={22}/></header><Table items={cases} searchText={c=>c.number+' '+c.document.name} status={c=>c.status} columns={[{title:'Perkara',render:c=><div className="stacked"><strong>{c.number}</strong><small>{c.document.name}</small></div>},{title:'Dibuat',render:c=>date(c.created_at)},{title:'Verifikasi',render:c=><Badge>{c.verified?'Terverifikasi':'Menunggu'}</Badge>},{title:'Status',render:c=><Badge>{c.status}</Badge>},{title:'Laporan',render:c=><div className="row-actions"><a aria-label={'PDF '+c.number} title="Pratinjau / unduh PDF" href={'/api/cases/'+c.id+'/report'} target="_blank" rel="noreferrer"><FileDown size={18}/></a><button title="Buka perkara" aria-label={'Buka '+c.number} onClick={()=>go('case/'+c.id)}><FolderOpen size={18}/></button></div>}]} emptyTitle="Belum ada laporan"/></section>;
}
