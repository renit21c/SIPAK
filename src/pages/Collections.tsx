import {FileDown,FolderOpen} from 'lucide-react';
import {Badge,Table} from '../components';
import {date,type Case} from '../types';
export function ReportsPage({cases,go}:{cases:Case[];go:(route:string)=>void}){
 return <section className="panel"><header className="panel-heading"><h2>Dokumen Rekomendasi</h2><FileDown size={22}/></header><Table items={cases} searchText={c=>c.number+' '+c.document.name} status={c=>c.recommendation_ready?'Siap diunduh':'Perlu evaluasi'} columns={[
  {title:'Perkara',render:c=><div className="stacked"><strong>{c.number}</strong><small>{c.document.name}</small></div>},
  {title:'Evaluasi terakhir',render:c=>c.evaluation?date(c.evaluation.created_at):'—'},
  {title:'Status',render:c=><Badge>{c.recommendation_ready?'Rekomendasi Siap':'Perlu Evaluasi'}</Badge>},
  {title:'Dokumen',render:c=><div className="row-actions">{c.recommendation_ready&&<a aria-label={'Unduh rekomendasi '+c.number} title="Rekomendasi PDF" href={'/api/cases/'+c.id+'/recommendation'} target="_blank" rel="noreferrer"><FileDown size={18}/></a>}<button aria-label={'Buka '+c.number} title="Buka evaluasi" onClick={()=>go('case/'+c.id+'?tab='+(c.recommendation_ready?'recommendation':'evaluation'))}><FolderOpen size={18}/></button></div>},
 ]} emptyTitle="Belum ada perkara untuk direkomendasikan"/></section>;
}
