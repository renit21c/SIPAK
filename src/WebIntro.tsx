import {useCallback,useEffect,useRef,useState,type ReactNode} from 'react';
import {Play,Volume2,VolumeX} from 'lucide-react';
import './web-intro.css';

const SESSION_KEY='sipak-intro-white-v1';
type Phase='ready'|'playing'|'leaving'|'done';
function initialPhase():Phase{
 if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return 'done';
 try{if(sessionStorage.getItem(SESSION_KEY)==='seen')return 'done'}catch{}
 return 'ready';
}

export function WebIntro({children}:{children:ReactNode}){
 const [phase,setPhase]=useState<Phase>(initialPhase),[muted,setMuted]=useState(false);
 const video=useRef<HTMLVideoElement>(null),content=useRef<HTMLDivElement>(null),overlay=useRef<HTMLDivElement>(null);
 const hadIntro=useRef(phase!=='done');
 const visible=phase!=='done';
 useEffect(()=>{
  if(!visible)return;
  const previous=document.body.style.overflow;document.body.style.overflow='hidden';
  return()=>{document.body.style.overflow=previous};
 },[visible]);
 const finish=useCallback(()=>{
  try{sessionStorage.setItem(SESSION_KEY,'seen')}catch{}
  setPhase(current=>current==='done'||current==='leaving'?current:'leaving');
 },[]);
 useEffect(()=>{
  if(phase==='playing'){const timer=setTimeout(finish,15000);return()=>clearTimeout(timer)}
  if(phase==='leaving'){const timer=setTimeout(()=>setPhase('done'),850);return()=>clearTimeout(timer)}
  if(phase==='done'&&hadIntro.current){video.current?.pause();content.current?.querySelector<HTMLElement>('input,button,a')?.focus({preventScroll:true});hadIntro.current=false}
 },[phase,finish]);
 useEffect(()=>{
  const preference=window.matchMedia('(prefers-reduced-motion: reduce)');
  const change=()=>{if(preference.matches){video.current?.pause();finish();setPhase('done')}};
  preference.addEventListener('change',change);return()=>preference.removeEventListener('change',change);
 },[finish]);
 const start=()=>{
  if(!video.current)return;
  video.current.volume=.7;video.current.muted=false;setMuted(false);
  setPhase('playing');video.current.play().catch(()=>setPhase(current=>current==='playing'?'ready':current));
 };
 const skip=()=>{video.current?.pause();finish()};
 const active=phase!=='done'&&phase!=='leaving';
 return <>
  <div ref={content} className={'intro-web-content '+(active?'intro-web-hidden':'intro-web-visible')} inert={active} aria-hidden={active||undefined}>{children}</div>
  {phase!=='done'&&<div ref={overlay} className={'web-intro '+(phase==='leaving'?'web-intro-leaving':'')} role="dialog" aria-modal={phase!=='leaving'} aria-label="Intro SIPAK" onTransitionEnd={e=>{if(e.target===e.currentTarget&&e.propertyName==='opacity'&&phase==='leaving')setPhase('done')}} onKeyDown={e=>{
   if(e.key==='Escape'){e.preventDefault();skip()}
   if(e.key==='Tab'){
    const buttons=overlay.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)');if(!buttons?.length)return;
    const first=buttons[0],last=buttons[buttons.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
   }
  }}>
   <video ref={video} src="/intro/sipak-intro.mp4" poster="/intro/poster.jpg" playsInline preload="auto" disablePictureInPicture aria-hidden="true" onEnded={finish} onError={finish} onTimeUpdate={()=>{if(video.current&&video.current.currentTime>=4.42)finish()}}/>
   {phase==='ready'&&<button className="intro-play" autoFocus onClick={start} aria-label="Putar intro dengan suara"><Play size={18} fill="currentColor"/>Mulai</button>}
   {phase!=='leaving'&&<div className="intro-controls">{phase==='playing'&&<button className="intro-sound" aria-label={muted?'Aktifkan suara':'Bisukan suara'} onClick={()=>{if(video.current){video.current.muted=!muted;setMuted(!muted)}}}>{muted?<VolumeX size={20}/>:<Volume2 size={20}/>}</button>}<button className="intro-skip" onClick={skip}>Lewati</button></div>}
  </div>}
 </>;
}
