import {LayoutDashboard,ScanText,FolderOpen,Scale,Gavel,History,BookOpen,Settings,Users,ScrollText,ClipboardCheck,FileDown,ShieldCheck,FileSearch,Eye,UserRound,type LucideIcon} from 'lucide-react';
import type {User,Doc,Case} from './types';

export type AppPage='dashboard'|'extraction'|'cases'|'analysis'|'sanctions'|'history'|'regulations'|'settings'|'verification'|'decisions'|'reports'|'users'|'audit';
type RoleProfile={label:string;workspace:string;heading:string;icon:LucideIcon;pages:AppPage[];primary:{page:AppPage;label:string;icon:LucideIcon};secondary:{page:AppPage;label:string;icon:LucideIcon};actions:AppPage[]};
export const pageDefinitions:Record<AppPage,{name:string;icon:LucideIcon;permission:string}>={
 dashboard:{name:'Dashboard',icon:LayoutDashboard,permission:'read'},
 extraction:{name:'Ekstraksi BAP',icon:ScanText,permission:'upload'},
 cases:{name:'Data Perkara',icon:FolderOpen,permission:'read'},
 analysis:{name:'Analisis Pelanggaran',icon:Scale,permission:'analyze'},
 sanctions:{name:'Pemeriksaan & Sanksi',icon:Gavel,permission:'review'},
 history:{name:'Riwayat Dokumen',icon:History,permission:'read'},
 regulations:{name:'Regulasi',icon:BookOpen,permission:'read'},
 settings:{name:'Pengaturan',icon:Settings,permission:'read'},
 verification:{name:'Antrean Verifikasi',icon:ClipboardCheck,permission:'review'},
 decisions:{name:'Antrean Keputusan',icon:Gavel,permission:'decide'},
 reports:{name:'Laporan',icon:FileDown,permission:'read'},
 users:{name:'Kelola Pengguna',icon:Users,permission:'users'},
 audit:{name:'Jejak Audit',icon:ScrollText,permission:'users'},
};
const profiles:Record<string,RoleProfile>={
 admin:{label:'Administrator',workspace:'Administrasi Sistem',heading:'Kontrol sistem, satu tempat.',icon:ShieldCheck,pages:['dashboard','users','audit','settings','extraction','cases','analysis','sanctions','history','regulations','reports'],primary:{page:'users',label:'Kelola Pengguna',icon:Users},secondary:{page:'settings',label:'Provider AI',icon:Settings},actions:['users','audit','settings','regulations']},
 investigator:{label:'Pemeriksa',workspace:'Ruang Pemeriksaan',heading:'Dari BAP ke fakta perkara.',icon:FileSearch,pages:['dashboard','extraction','cases','analysis','history','regulations','reports','settings'],primary:{page:'extraction',label:'Unggah BAP',icon:ScanText},secondary:{page:'cases',label:'Data Perkara',icon:FolderOpen},actions:['extraction','cases','analysis','history']},
 reviewer:{label:'Verifikator',workspace:'Ruang Verifikasi',heading:'Periksa sumber. Validasi fakta.',icon:ClipboardCheck,pages:['dashboard','verification','cases','analysis','sanctions','extraction','history','regulations','reports','settings'],primary:{page:'verification',label:'Mulai Verifikasi',icon:ClipboardCheck},secondary:{page:'sanctions',label:'Pemeriksaan',icon:Scale},actions:['verification','cases','analysis','sanctions']},
 decision_maker:{label:'Pejabat Berwenang',workspace:'Ruang Keputusan',heading:'Telaah lengkap, keputusan tercatat.',icon:Gavel,pages:['dashboard','decisions','sanctions','cases','analysis','reports','regulations','settings'],primary:{page:'decisions',label:'Tinjau Keputusan',icon:Gavel},secondary:{page:'sanctions',label:'Lihat Pemeriksaan',icon:ClipboardCheck},actions:['decisions','sanctions','reports','regulations']},
 viewer:{label:'Pengamat',workspace:'Ruang Pemantauan',heading:'Pantau perkara dan laporan.',icon:Eye,pages:['dashboard','cases','reports','history','regulations','settings'],primary:{page:'cases',label:'Lihat Perkara',icon:FolderOpen},secondary:{page:'reports',label:'Laporan PDF',icon:FileDown},actions:['cases','reports','history','regulations']},
};

export const roleProfile=(user:User)=>profiles[user.role]||profiles.viewer;
export const canOpen=(user:User,page:string):page is AppPage=>!!pageDefinitions[page as AppPage]&&roleProfile(user).pages.includes(page as AppPage)&&user.permissions.includes(pageDefinitions[page as AppPage].permission);
export const roleNavigation=(user:User)=>roleProfile(user).pages.filter(page=>canOpen(user,page)).map(id=>({id,...pageDefinitions[id],name:id==='settings'&&!user.permissions.includes('users')?'Akun Saya':pageDefinitions[id].name}));
export const accountIcon=UserRound;

export function roleHelp(user:User):string[]{
 const guides:Record<string,string[]>={
  admin:['Kelola akun dan peran melalui Kelola Pengguna.','Atur provider AI di Pengaturan; pantau aktivitas melalui Jejak Audit.','Keputusan resmi hanya dapat dicatat pejabat berwenang.'],
  investigator:['Unggah BAP berteks, lalu pantau status pemrosesannya.','Periksa hasil dan sumber BAP sebelum memasukkan fakta analisis.','Serahkan hasil untuk verifikasi dan pemeriksaan lanjutan.'],
  reviewer:['Buka Antrean Verifikasi dan cocokkan hasil dengan kutipan sumber.','Simpan koreksi atau verifikasi hasil; catat alasan telaah.','Lengkapi pemeriksaan dan dokumen pendukung sebelum rekomendasi.'],
  decision_maker:['Buka Antrean Keputusan untuk perkara yang telah melalui pemeriksaan.','Telaah bukti, ketentuan dan rekomendasi sebelum mencatat keputusan.','Keputusan resmi dikunci setelah dicatat; penyampaian tetap dilengkapi.'],
  viewer:['Buka Data Perkara untuk melihat informasi dan sumber dokumen.','Laporan dapat dipratinjau dan diunduh melalui menu Laporan.','Akun pengamat tidak dapat mengubah hasil, pemeriksaan atau keputusan.'],
 };
 return guides[user.role]||guides.viewer;
}

export function roleNotice(user:User,docs:Doc[],cases:Case[]):{count:number;text:string;page:AppPage}{
 const pending=cases.filter(c=>!c.verified).length,failed=docs.filter(d=>d.status==='Gagal').length,ready=cases.filter(c=>c.status==='Menunggu Keputusan Berwenang').length,issued=cases.filter(c=>c.status==='Keputusan Resmi Diterbitkan').length;
 if(user.role==='reviewer')return {count:pending,text:pending?pending+' perkara menunggu verifikasi.':'Tidak ada antrean verifikasi.',page:'verification'};
 if(user.role==='decision_maker')return {count:ready,text:ready?ready+' perkara siap ditinjau untuk keputusan.':'Tidak ada perkara menunggu keputusan.',page:'decisions'};
 if(user.role==='investigator')return {count:failed,text:failed?failed+' dokumen gagal diproses.':'Tidak ada dokumen gagal.',page:'history'};
 if(user.role==='admin')return {count:failed,text:failed?failed+' kegagalan pemrosesan perlu diperiksa.':'Tidak ada kegagalan pemrosesan.',page:'audit'};
 return {count:issued,text:issued?issued+' keputusan tercatat dalam laporan.':'Belum ada keputusan tercatat.',page:'reports'};
}
