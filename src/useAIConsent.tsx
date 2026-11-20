import {useState} from 'react';
import {Cloud,FileText,LoaderCircle} from 'lucide-react';
import {api} from './api';
import {Modal} from './components';
import type {Settings} from './types';

type Action=(config:Settings,consent:boolean)=>Promise<void>;
export const inferencePayload=(config:Settings,consent:boolean)=>({cloud_consent:consent,expected_provider:config.ai_provider,expected_model:config.model});
export function useAIConsent(notify:(message:string)=>void){
 const [pending,setPending]=useState<{name:string;config:Settings;run:Action}|null>(null),[accepted,setAccepted]=useState(false),[busy,setBusy]=useState(false);
 const request=async(name:string,run:Action)=>{try{const config=await api<Settings>('/settings');if(!config.ai_configured)throw new Error('Lengkapi provider, model, dan API key di Pengaturan terlebih dahulu.');if(config.ai_external){setAccepted(false);setPending({name,config,run})}else await run(config,false)}catch(e){notify((e as Error).message)}};
 const dialog=pending&&<Modal title="Kirim BAP ke OpenRouter?" close={()=>{if(!busy)setPending(null)}}><div className="modal-body"><div className="consent-document"><FileText size={22}/><strong>{pending.name}</strong></div><dl className="detail-fields"><div><dt>Penerima</dt><dd>OpenRouter dan penyedia model yang dirutekannya</dd></div><div><dt>Model</dt><dd><code>{pending.config.model}</code></dd></div></dl><p className="muted">Teks BAP, termasuk identitas, keterangan, barang bukti, dan kronologi, akan dikirim ke {pending.config.ai_endpoint}. Biaya mengikuti penggunaan API.</p><label className="checkbox consent-checkbox"><input type="checkbox" checked={accepted} disabled={busy} onChange={e=>setAccepted(e.target.checked)}/><span>Saya berwenang dan menyetujui pengiriman dokumen ini ke provider tersebut.</span></label><div className="form-actions"><button className="btn secondary" disabled={busy} onClick={()=>setPending(null)}>Batal</button><button className="btn primary" disabled={!accepted||busy} onClick={async()=>{setBusy(true);try{await pending.run(pending.config,true);setPending(null)}catch(e){notify((e as Error).message)}finally{setBusy(false)}}}>{busy?<LoaderCircle size={16} className="spin"/>:<Cloud size={16}/>}Kirim & Proses</button></div></div></Modal>;
 return {request,dialog};
}
