import {useEffect,useRef,useState} from 'react';
import {Ellipsis,X,ChevronRight} from 'lucide-react';
import {pageDefinitions,canOpen,type AppPage} from './roles';
import type {User} from './types';
import './mobile-navigation.css';

const primary:AppPage[]=['dashboard','cases','extraction','reports'];
const secondary:AppPage[]=['history','regulations','settings'];
const labels:Partial<Record<AppPage,string>>={dashboard:'Ringkasan',extraction:'Unggah',reports:'Rekomendasi'};

export function MobileNavigation({user,active}:{user:User;active:string}){
 const [open,setOpen]=useState(false),dialog=useRef<HTMLDialogElement>(null);
 const main=primary.filter(page=>canOpen(user,page)),more=secondary.filter(page=>canOpen(user,page));
 useEffect(()=>{const sheet=dialog.current;if(open&&!sheet?.open)sheet?.showModal();else if(!open&&sheet?.open)sheet.close()},[open]);
 useEffect(()=>{setOpen(false)},[active]);
 useEffect(()=>{const desktop=matchMedia('(min-width:761px)');const close=()=>{if(desktop.matches)setOpen(false)};desktop.addEventListener('change',close);return()=>desktop.removeEventListener('change',close)},[]);
 const moreActive=more.includes(active as AppPage)||active==='users'||active==='audit';
 return <>
  <nav className="mobile-bottom-nav" aria-label="Navigasi utama mobile" style={{gridTemplateColumns:`repeat(${main.length+(more.length?1:0)},minmax(0,1fr))`}}>
   {main.map(page=>{const Icon=pageDefinitions[page].icon;return <a href={'#'+page} key={page} className={active===page&&!open?'active':''} aria-current={active===page?'page':undefined} aria-label={pageDefinitions[page].name}><span className="bottom-nav-icon"><Icon size={22}/></span><span className="bottom-nav-label">{labels[page]||pageDefinitions[page].name}</span></a>})}
   {!!more.length&&<button type="button" className={moreActive||open?'active':''} aria-label="Lainnya" aria-haspopup="dialog" aria-expanded={open} onClick={()=>setOpen(true)}><span className="bottom-nav-icon"><Ellipsis size={23}/></span><span className="bottom-nav-label">Lainnya</span></button>}
  </nav>
  <dialog ref={dialog} className="mobile-nav-sheet" aria-labelledby="mobile-more-title" onCancel={()=>setOpen(false)} onClose={()=>setOpen(false)} onClick={event=>{if(event.target===event.currentTarget){const bounds=event.currentTarget.getBoundingClientRect();if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)setOpen(false)}}}>
   <header><h2 id="mobile-more-title">Lainnya</h2><button type="button" className="icon-btn" aria-label="Tutup menu lainnya" autoFocus onClick={()=>setOpen(false)}><X size={20}/></button></header>
   <nav aria-label="Menu lainnya">{more.map(page=>{const Icon=pageDefinitions[page].icon;return <a key={page} href={'#'+page} aria-current={active===page?'page':undefined} onClick={()=>setOpen(false)}><span className="more-nav-icon"><Icon size={21}/></span><strong>{pageDefinitions[page].name}</strong><ChevronRight size={17}/></a>})}</nav>
  </dialog>
 </>;
}
