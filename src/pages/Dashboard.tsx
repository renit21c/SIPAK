import {UploadCloud,ClipboardCheck,FileDown,FolderOpen,Clock3,FileText} from 'lucide-react';
import type {Doc,Case,Settings,User} from '../types';
import {Badge,Table} from '../components';
import {text} from '../types';

export function Dashboard({docs,cases,go}:{docs:Doc[];cases:Case[];go:(v:string)=>void;settings:Settings|null;user:User}){
 const active=docs.filter(d=>['Menunggu','Sedang Diproses'].includes(d.status)),pending=cases.filter(c=>!c.recommendation_ready),ready=cases.filter(c=>c.recommendation_ready);
 const stats=[{label:'Perkara',value:cases.length,icon:FolderOpen},{label:'Diproses',value:active.length,icon:Clock3},{label:'Perlu Evaluasi',value:pending.length,icon:ClipboardCheck},{label:'Rekomendasi Siap',value:ready.length,icon:FileDown}];
 return <>
  <section className="komdis-intro"><div><span className="section-kicker">KOMISI DISIPLIN</span><h2>BAP masuk. Telaah tuntas.</h2></div><button className="btn primary" onClick={()=>go('extraction')}><UploadCloud size={19}/>Unggah BAP</button></section>
  <div className="case-steps overview-steps"><span><UploadCloud size={18}/>Unggah</span><span><FileText size={18}/>Proses BAP</span><span><ClipboardCheck size={18}/>Evaluasi</span><span><FileDown size={18}/>Rekomendasi</span></div>
  <div className="stats-grid">{stats.map(s=><section className="stat-card" key={s.label}><div className="stat-top"><span>{s.label}</span><div className="stat-icon indigo"><s.icon size={21}/></div></div><strong>{s.value}</strong></section>)}</div>
  {!!active.length&&<div className="alert"><Clock3 size={18}/>{active.length} BAP sedang diproses.<button className="text-btn" onClick={()=>go('history')}>Lihat proses</button></div>}
  <section className="panel"><header className="panel-heading"><h2>Perkara Terbaru</h2><button className="text-btn" onClick={()=>go('cases')}>Lihat semua</button></header><Table items={cases.slice(0,10)} searchText={c=>c.number+' '+c.document.name+' '+c.persons.map(p=>p.name).join(' ')} status={c=>c.recommendation_ready?'Rekomendasi Siap':c.status} columns={[
   {title:'Perkara',render:c=><div className="stacked"><strong>{c.number}</strong><small>{c.document.name}</small></div>},
   {title:'Pihak terkait',render:c=>c.persons.slice(0,2).map(p=>text(p.name)).join(', ')||'—'},
   {title:'Status',render:c=><Badge>{c.recommendation_ready?'Rekomendasi Siap':c.status}</Badge>},
   {title:'Tindakan',render:c=><button className="btn secondary" onClick={()=>go('case/'+c.id+'?tab='+(c.recommendation_ready?'recommendation':'overview'))}>{c.recommendation_ready?<FileDown size={16}/>:<ClipboardCheck size={16}/>} {c.recommendation_ready?'Rekomendasi':'Telaah'}</button>},
  ]} emptyTitle="Belum ada perkara"/></section>
 </>;
}
