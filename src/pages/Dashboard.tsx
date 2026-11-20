import {ClipboardCheck,FileDown,FolderOpen,Clock3} from 'lucide-react';
import type {Doc,Case,Settings,User} from '../types';
import {Badge,Table} from '../components';
import {text} from '../types';

export function Dashboard({docs,cases,go}:{docs:Doc[];cases:Case[];go:(v:string)=>void;settings:Settings|null;user:User}){
 const active=docs.filter(d=>['Menunggu','Sedang Diproses'].includes(d.status)),pending=cases.filter(c=>!c.recommendation_ready),ready=cases.filter(c=>c.recommendation_ready);
 const stats=[{label:'Perkara',value:cases.length,icon:FolderOpen,page:'cases',tone:'neutral'},{label:'Diproses',value:active.length,icon:Clock3,page:'history',tone:'processing'},{label:'Perlu Telaah',value:pending.length,icon:ClipboardCheck,page:'cases',tone:'attention'},{label:'Rekomendasi Siap',value:ready.length,icon:FileDown,page:'reports',tone:'ready'}];
 return <>

  <div className="stats-grid">{stats.map(s=><button className={'stat-card stat-'+(s.value?s.tone:'neutral')} key={s.label} onClick={()=>go(s.page)} aria-label={s.label+': '+s.value}><div className="stat-top"><span>{s.label}</span><div className="stat-icon indigo"><s.icon size={21}/></div></div><strong>{s.value}</strong></button>)}</div>
  {!!active.length&&<div className="alert"><Clock3 size={18}/>{active.length} BAP sedang diproses.<button className="text-btn" onClick={()=>go('history')}>Lihat proses</button></div>}
  <section className="panel"><header className="panel-heading"><h2>Perkara Terbaru</h2><button className="text-btn" onClick={()=>go('cases')}>Lihat semua</button></header><Table items={cases.slice(0,10)} searchText={c=>c.number+' '+c.document.name+' '+c.persons.map(p=>p.name).join(' ')} status={c=>c.recommendation_ready?'Rekomendasi Siap':c.status} columns={[
   {title:'Perkara',render:c=><div className="stacked"><strong>{c.number}</strong><small>{c.document.name}</small></div>},
   {title:'Pihak terkait',render:c=>c.persons.slice(0,2).map(p=>text(p.name)).join(', ')||'—'},
   {title:'Status',render:c=><Badge>{c.recommendation_ready?'Rekomendasi Siap':c.status}</Badge>},
   {title:'Tindakan',render:c=><button className="btn secondary" onClick={()=>go('case/'+c.id+'?tab='+(c.recommendation_ready?'recommendation':'overview'))}>{c.recommendation_ready?<FileDown size={16}/>:<ClipboardCheck size={16}/>} {c.recommendation_ready?'Rekomendasi':'Telaah'}</button>},
  ]} emptyTitle="Belum ada perkara"/></section>
 </>;
}
