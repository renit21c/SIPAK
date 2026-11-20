import {useCallback,useEffect,useRef,useState,type ReactNode} from 'react';
import './web-intro.css';

type Phase='playing'|'leaving'|'done';
function initialPhase():Phase{
 if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return 'done';
 return 'playing';
}

export function WebIntro({children}:{children:ReactNode}){
 const [phase,setPhase]=useState<Phase>(initialPhase),[muted,setMuted]=useState(false);
 const video=useRef<HTMLVideoElement>(null),content=useRef<HTMLDivElement>(null);
 const hadIntro=useRef(phase!=='done');
 const visible=phase!=='done';
 useEffect(()=>{
  if(!visible)return;
  const previous=document.body.style.overflow;document.body.style.overflow='hidden';
  return()=>{document.body.style.overflow=previous};
 },[visible]);
 const finish=useCallback(()=>{
  setPhase(current=>current==='done'||current==='leaving'?current:'leaving');
 },[]);
 useEffect(()=>{
  if(phase!=='playing'||!video.current)return;
  const player=video.current;let cancelled=false;
  player.volume=.7;player.muted=false;
  player.play().catch(async()=>{
   if(cancelled)return;
   // Keep the intro automatic when browser policy rejects audible autoplay.
   player.muted=true;setMuted(true);
   try{await player.play()}catch{if(!cancelled)finish()}
  });
  return()=>{cancelled=true};
 },[phase,finish]);
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
 const active=phase!=='done'&&phase!=='leaving';
 return <>
  <div ref={content} className={'intro-web-content '+(active?'intro-web-hidden':'intro-web-visible')} inert={active} aria-hidden={active||undefined}>{children}</div>
  {phase!=='done'&&<div className={'web-intro '+(phase==='leaving'?'web-intro-leaving':'')} role="status" aria-label="Intro SIPAK" onTransitionEnd={e=>{if(e.target===e.currentTarget&&e.propertyName==='opacity'&&phase==='leaving')setPhase('done')}}>
   <video ref={video} src="/intro/sipak-intro.mp4" poster="/intro/poster.jpg" autoPlay muted={muted} playsInline preload="auto" disablePictureInPicture aria-hidden="true" onEnded={finish} onError={finish} onTimeUpdate={()=>{if(video.current&&video.current.currentTime>=4.42)finish()}}/>
  </div>}
 </>;
}
