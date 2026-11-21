import {useState} from 'react';
import {Cloud,FileText,LoaderCircle} from 'lucide-react';
import {api} from './api';
import {Modal} from './components';
import type {Settings} from './types';

type Action=(config:Settings,consent:boolean)=>Promise<void>;
export const inferencePayload=(config:Settings,consent:boolean,withOCR=false)=>({cloud_consent:consent,expected_provider:config.ai_provider,expected_model:config.model,ocr_consent:withOCR&&config.ocr_configured&&consent,expected_ocr_provider:withOCR?config.ocr_provider:''});
export function useAIConsent(notify:(message:string)=>void){
 const [pending,setPending]=useState<{name:string;config:Settings;run:Action;ocr:boolean}|null>(null),[accepted,setAccepted]=useState(false),[busy,setBusy]=useState(false);
 const request=async(name:string,run:Action,withOCR=false)=>{try{const config=await api<Settings>('/settings');if(!config.ai_configured)throw new Error('Lengkapi provider, model, dan API key di Pengaturan terlebih dahulu.');if(config.ai_external||(withOCR&&config.ocr_configured)){setAccepted(false);setPending({name,config,run,ocr:withOCR&&config.ocr_configured})}else await run(config,false)}catch(e){notify((e as Error).message)}};
 const dialog=pending&&<Modal title="Proses BAP dengan layanan ini?" close={()=>{if(!busy)setPending(null)}}><div className="modal-body"><div className="consent-document"><FileText size={22}/><strong>{pending.name}</strong></div><dl className="detail-fields"><div><dt>Penerima</dt><dd>{[pending.config.ai_external?'OpenRouter dan penyedia modelnya':'',pending.ocr?'FastOCR (halaman scan)':''].filter(Boolean).join(' · ')}</dd></div><div><dt>Model</dt><dd><code>{pending.config.model}</code></dd></div></dl><p className="muted">{pending.config.ai_external&&'Teks BAP, termasuk identitas dan keterangan, dikirim ke OpenRouter dan penyedia modelnya. '}{pending.ocr&&'Halaman PDF yang memerlukan OCR dikirim ke FastOCR. '}Biaya mengikuti penggunaan layanan.</p><label className="checkbox consent-checkbox"><input type="checkbox" checked={accepted} disabled={busy} onChange={e=>setAccepted(e.target.checked)}/><span>Saya berwenang dan menyetujui pengiriman dokumen ini ke provider tersebut.</span></label><div className="form-actions"><button className="btn secondary" disabled={busy} onClick={()=>setPending(null)}>Batal</button><button className="btn primary" disabled={!accepted||busy} onClick={async()=>{setBusy(true);try{await pending.run(pending.config,true);setPending(null)}catch(e){notify((e as Error).message)}finally{setBusy(false)}}}>{busy?<LoaderCircle size={16} className="spin"/>:<Cloud size={16}/>}Kirim & Proses</button></div></div></Modal>;
 return {request,dialog};
}
