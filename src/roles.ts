import {LayoutDashboard,ScanText,FolderOpen,History,BookOpen,Settings,Users,ScrollText,FileDown,Gavel} from 'lucide-react';
import type {User,Doc,Case} from './types';

export type AppPage='dashboard'|'extraction'|'cases'|'history'|'regulations'|'settings'|'reports'|'users'|'audit';
export const pageDefinitions={
 dashboard:{name:'Ringkasan',icon:LayoutDashboard,permission:'read'},
 extraction:{name:'Unggah BAP',icon:ScanText,permission:'upload'},
 cases:{name:'Perkara',icon:FolderOpen,permission:'read'},
 reports:{name:'Rekomendasi',icon:FileDown,permission:'read'},
 history:{name:'Arsip BAP',icon:History,permission:'read'},
 regulations:{name:'Regulasi',icon:BookOpen,permission:'read'},
 settings:{name:'Pengaturan',icon:Settings,permission:'users'},
 users:{name:'Anggota Komdis',icon:Users,permission:'users'},
 audit:{name:'Jejak Audit',icon:ScrollText,permission:'users'},
};
const pages:AppPage[]=['dashboard','extraction','cases','reports','history','regulations','settings'];
export const roleProfile=(_user:User)=>({label:'Komdis',workspace:'Ruang Komdis',icon:Gavel,pages});
export const canOpen=(user:User,page:string):page is AppPage=>Object.prototype.hasOwnProperty.call(pageDefinitions,page)&&user.permissions.includes(pageDefinitions[page as AppPage].permission);
export const roleNavigation=(user:User)=>pages.filter(page=>canOpen(user,page)).map(id=>({id,...pageDefinitions[id]}));
export const roleHelp=(_user:User)=>['Unggah BAP PDF dan tunggu hasil pemrosesan.','Periksa fakta dan kutipan sumber, lalu verifikasi hasil.','Lengkapi telaah ketentuan bila diperlukan. Simpan evaluasi: perbaiki atau lanjutkan.','Unduh rekomendasi PDF setelah evaluasi disetujui. Perubahan BAP atau analisis memerlukan evaluasi ulang.'];
export function roleNotice(_user:User,docs:Doc[],cases:Case[]):{count:number;text:string;page:AppPage}{
 const failed=docs.filter(d=>d.status==='Gagal').length,pending=cases.filter(c=>!c.recommendation_ready).length;
 return failed?{count:failed,text:failed+' BAP perlu diproses ulang.',page:'history'}:{count:pending,text:pending?pending+' perkara belum selesai dievaluasi.':'Semua evaluasi selesai.',page:'cases'};
}
