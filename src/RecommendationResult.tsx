import {FileDown,Scale,UserRound} from 'lucide-react';
import {Badge} from './components';
import {date,text,type Case} from './types';

export function RecommendationResult({caseData:c}:{caseData:Case}){
 if(!c.evaluation)return null;
 const result=c.evaluation.payload;
 return <section className="panel padded recommendation-panel result-panel">
  <header className="result-header"><span className="recommendation-icon"><FileDown size={25}/></span><div><h2>Rekomendasi Komdis</h2><p>{c.evaluation.created_by} · {date(c.evaluation.created_at)}</p></div><Badge>Rekomendasi Siap</Badge></header>
  {c.persons.length>0&&<div className="result-people">{c.persons.map((person,i)=><span key={i}><UserRound size={17}/><strong>{text(person.name)}</strong>{person.role!=null&&<small>{text(person.role)}</small>}</span>)}</div>}
  <div className="result-decision"><div className="result-category"><span>Kategori</span><Badge>{result.category}</Badge></div><div className="result-action"><span>Usulan tindakan</span><p>{result.sanction||'Tidak diusulkan'}</p></div></div>
  <section className="result-recommendation"><h3>Rekomendasi</h3><p>{result.recommendation}</p></section>
  <section className="result-summary"><h3>Ringkasan evaluasi</h3><p>{result.summary}</p></section>
  <section className="result-basis"><h3>Dasar pertimbangan</h3><p>{result.basis}</p><div className="selected-articles">{result.articles?.map(article=><article key={article.id}><details><summary><Scale size={17}/><span>Pasal {article.number}<small>{article.regulation_title}</small></span></summary><p>{article.text}</p></details></article>)}</div></section>
 </section>;
}
