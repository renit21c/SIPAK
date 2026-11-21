import {useEffect,useState,useCallback} from 'react';
import {FolderOpen,UploadCloud,Settings as SettingsIcon,Bell,ChevronDown,LogOut,LockKeyhole,HelpCircle,PanelLeftClose,CheckCircle2,AlertCircle,Eye,EyeOff} from 'lucide-react';
import {api,post} from './api';
import {MobileNavigation} from './MobileNavigation';
import {Logo,Modal,Field,Loading} from './components';
import type {User,Doc,Case,Settings} from './types';
import {Dashboard} from './pages/Dashboard';
import {ExtractionPage} from './pages/Extraction';
import {CasesPage,CaseDetail} from './pages/Cases';
import {HistoryPage,SettingsPage} from './pages/Management';
import {RegulationsPage} from './pages/Regulations';
import {ReportsPage} from './pages/Collections';
import {roleProfile,roleNavigation,canOpen,pageDefinitions,roleNotice,roleHelp,type AppPage} from './roles';


export default function App(){
 const [user,setUser]=useState<User|null>(null),[authLoaded,setAuthLoaded]=useState(false),[route,setRoute]=useState(location.hash.slice(1)||'dashboard');
 const [docs,setDocs]=useState<Doc[]>([]),[cases,setCases]=useState<Case[]>([]),[settings,setSettings]=useState<Settings|null>(null),[dataLoaded,setDataLoaded]=useState(false),[error,setError]=useState('');
 const [collapsed,setCollapsed]=useState(false),[profile,setProfile]=useState(false),[notifications,setNotifications]=useState(false),[help,setHelp]=useState(false),[toast,setToast]=useState('');
 useEffect(()=>{api<User>('/auth/me').then(setUser).catch(()=>{}).finally(()=>setAuthLoaded(true));const onHash=()=>{setRoute(location.hash.slice(1)||'dashboard');setProfile(false);setNotifications(false)};window.addEventListener('hashchange',onHash);return()=>window.removeEventListener('hashchange',onHash)},[]);
 const refresh=useCallback(async()=>{try{const [d,c]=await Promise.all([api<Doc[]>('/documents'),api<Case[]>('/cases')]);setDocs(d);setCases(c);setError('');setDataLoaded(true)}catch(e){setError((e as Error).message)}},[]);
 useEffect(()=>{if(!user)return;refresh();api<Settings>('/settings').then(setSettings).catch(()=>{});const timer=setInterval(()=>{if(!document.hidden)refresh()},5000);return()=>clearInterval(timer)},[user,refresh]);
 useEffect(()=>{if(toast){const timer=setTimeout(()=>setToast(''),5000);return()=>clearTimeout(timer)}},[toast]);
 const go=(v:string)=>{location.hash=v};const notify=(v:string)=>setToast(v);
 const logout=async()=>{try{await post('/auth/logout');setUser(null);setDataLoaded(false);setProfile(false)}catch(e){notify((e as Error).message)}};
 if(!authLoaded)return <Loading/>;
 if(!user)return <Login onLogin={value=>{setUser(value);setSettings(null);go('dashboard')}}/>;
 const active=route.startsWith('case/')?'cases':route;const navigation=roleNavigation(user),profileInfo=roleProfile(user),RoleIcon=profileInfo.icon;const page=navigation.find(n=>n.id===active)||{id:active,name:pageDefinitions[active as AppPage]?.name||'Halaman',icon:FolderOpen};const allowed=canOpen(user,active);const notice=roleNotice(user,docs,cases);
 const pending=notice.count;
 return <div className={'app role-komdis '+(collapsed?'collapsed ':'')}>
   <aside className="sidebar" id="desktop-navigation"><a href="#dashboard" className="brand-link" aria-label="SIPAK Dashboard"><Logo/></a><div className="workspace-label role-workspace-label"><RoleIcon size={14}/><span>{profileInfo.label}</span></div><nav>{navigation.map((n,i)=><a key={n.id} href={'#'+n.id} title={n.name} className={active===n.id?'active':''}><n.icon size={20}/><span>{n.name}</span>{n.id==='extraction'&&<small>AI</small>}{i===4&&<i/>}</a>)}</nav><div className="sidebar-bottom"><button className="collapse-btn" aria-controls="desktop-navigation" aria-expanded={!collapsed} title={collapsed?'Perluas menu':'Ciutkan menu'} aria-label={collapsed?'Perluas menu':'Ciutkan menu'} onClick={()=>setCollapsed(!collapsed)}><PanelLeftClose size={18}/><span>Ciutkan menu</span></button></div></aside>
   <div className="main-shell"><header className="topbar"><div className="breadcrumb"><strong>{page.name}</strong></div><div className="topbar-right"><button className={'icon-btn notification '+(pending?'has-notification':'')} aria-label="Notifikasi" onClick={()=>setNotifications(!notifications)}><Bell size={20}/></button><div className="topbar-divider"/><button className="profile" onClick={()=>setProfile(!profile)}><span className="avatar">{user.name.split(' ').map(n=>n[0]).slice(0,2).join('')}</span><span><strong>{user.name}</strong><small>{profileInfo.label}</small></span><ChevronDown size={15}/></button></div>{profile&&<div className="popover profile-pop"><strong>{user.name}</strong><p>{user.email}</p><button onClick={()=>{go('settings');setProfile(false)}}><SettingsIcon size={16}/>Pengaturan akun</button><button onClick={logout}><LogOut size={16}/>Keluar</button></div>}{notifications&&<div className="popover notification-pop"><h3>Notifikasi</h3><p>{notice.text}</p><button className="text-btn" onClick={()=>{go(notice.page);setNotifications(false)}}>Buka {pageDefinitions[notice.page].name}</button></div>}</header>
   <main><div key={route} className="page-content"><div className="page-heading"><div><h1>{!allowed?'Akses Terbatas':route.startsWith('case/')?'Detail Perkara':active==='dashboard'?'Ringkasan':page.name}</h1></div>{active==='dashboard'&&user.permissions.includes('upload')&&<button className="btn primary" onClick={()=>go('extraction')}><UploadCloud size={18}/>Unggah BAP</button>}</div>
   {error&&<div className="alert error"><AlertCircle size={18}/>{error}<button onClick={refresh}>Coba kembali</button></div>}
   {!allowed?<section className="panel"><div className="empty"><LockKeyhole size={32}/><h3>Halaman tidak tersedia untuk peran ini</h3><button className="btn secondary" onClick={()=>go('dashboard')}>Kembali ke Dashboard</button></div></section>:!dataLoaded?<Loading/>:route.startsWith('case/')?<CaseDetail id={route.split('/')[1]} user={user} settings={settings} notify={notify} refresh={refresh}/>:active==='dashboard'?<Dashboard docs={docs} cases={cases} go={go} settings={settings} user={user}/>:active==='reports'?<ReportsPage cases={cases} go={go}/>:active==='extraction'?<ExtractionPage docs={docs} settings={settings} user={user} refresh={refresh} go={go} notify={notify}/>:active==='cases'?<CasesPage cases={cases} go={go} mode={active} user={user} refresh={refresh} notify={notify}/>:active==='history'?<HistoryPage docs={docs} user={user} go={go} refresh={refresh} notify={notify}/>:active==='regulations'?<RegulationsPage user={user} notify={notify}/>:<SettingsPage user={user} settings={settings} notify={notify} onSettingsChange={setSettings} section={active==='users'?'users':active==='audit'?'audit':'settings'}/>}
   </div><footer className="app-footer"><span>SIPAK · {new Date().getFullYear()}</span><button title="Panduan penggunaan" aria-label="Panduan penggunaan" onClick={()=>setHelp(true)}><HelpCircle size={18}/></button></footer></main></div>
   <MobileNavigation user={user} active={active}/>
   {toast&&<div role="status" className="toast"><CheckCircle2 size={18}/>{toast}<button onClick={()=>setToast('')} aria-label="Tutup notifikasi">×</button></div>}
   {help&&<Modal title="Panduan penggunaan SIPAK" close={()=>setHelp(false)}><div className="modal-body prose"><ul>{roleHelp(user).map(step=><li key={step}>{step}</li>)}</ul>{user.permissions.includes('upload')&&<div className="alert">Gunakan PDF berteks. PDF pindai belum didukung.</div>}</div></Modal>}
 </div>
}

function Login({onLogin}:{onLogin:(u:User)=>void}){
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[showPassword,setShowPassword]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 return <div className="login-screen"><div className="login">
  <div className="login-story"><div className="login-brand-row"><Logo/></div><div className="login-narrative"><h1>Ruang kerja<br/><em>Komdis.</em></h1></div></div>
  <div className="login-form"><h2>Masuk</h2><form onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{onLogin(await post<User>('/auth/login',{email,password}))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>
   <Field label="Email"><input autoComplete="username" type="email" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="nama@institusi.ac.id"/></Field>
   <div className="field"><label htmlFor="login-password">Kata sandi</label><div className="password-input"><input id="login-password" autoComplete="current-password" type={showPassword?'text':'password'} required value={password} onChange={e=>setPassword(e.target.value)} placeholder="Kata sandi"/><button type="button" className="icon-btn" aria-label={showPassword?'Sembunyikan kata sandi':'Lihat kata sandi'} aria-pressed={showPassword} onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff size={19}/>:<Eye size={19}/>}</button></div></div>
   {error&&<div role="alert" className="alert error">{error}</div>}<button className="btn primary" disabled={busy}>{busy?'Memeriksa…':'Masuk'}</button>
  </form></div>
 </div></div>;
}
