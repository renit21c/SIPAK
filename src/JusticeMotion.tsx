import {useEffect,useState} from 'react';
import {Pause,Play} from 'lucide-react';

export function MotionControl(){
 const [paused,setPaused]=useState(()=>{try{return localStorage.getItem('sipak-motion')==='paused'}catch{return false}});
 useEffect(()=>{document.documentElement.dataset.motion=paused?'paused':'on';try{localStorage.setItem('sipak-motion',paused?'paused':'on')}catch{}},[paused]);
 return <button className="icon-btn motion-control" type="button" aria-label={paused?'Aktifkan animasi':'Jeda animasi'} title={paused?'Aktifkan animasi':'Jeda animasi'} aria-pressed={paused} onClick={()=>setPaused(!paused)}>{paused?<Play size={17}/>:<Pause size={17}/>}</button>;
}

export function JusticeMotion(){
 return <div className="justice-scene" aria-hidden="true">
  <div className="justice-halo"/><div className="justice-orbit"/>
  <svg className="justice-art" viewBox="0 0 560 280" fill="none">
   <defs>
    <linearGradient id="gavel-metal" x1="145" y1="80" x2="290" y2="190" gradientUnits="userSpaceOnUse"><stop stopColor="#FFD9A6"/><stop offset="1" stopColor="#B77C46"/></linearGradient>
    <linearGradient id="justice-paper" x1="335" y1="80" x2="435" y2="240" gradientUnits="userSpaceOnUse"><stop stopColor="#F5F1FF"/><stop offset="1" stopColor="#B5B6DC"/></linearGradient>
   </defs>
   <ellipse cx="274" cy="247" rx="219" ry="12" fill="#15173E" opacity=".35"/>
   <g className="justice-paper">
    <rect x="339" y="89" width="103" height="139" rx="10" fill="#777CA7" transform="rotate(9 390 160)"/>
    <path d="M336 82H406L433 110V213Q433 223 423 223H336Q326 223 326 213V92Q326 82 336 82Z" fill="url(#justice-paper)"/>
    <path d="M405 83V110H432" stroke="#9298C0" strokeWidth="3" strokeLinejoin="round"/>
    <path d="M345 142H410M345 157H402M345 172H388" stroke="#8B90B6" strokeWidth="4" strokeLinecap="round"/>
    <circle cx="401" cy="199" r="12" fill="#DA7E93"/><path d="M395 199L399 203L407 195" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
   </g>
   <g className="justice-scales" stroke="#B9BFDF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M102 94V199M80 202H124M76 113H128"/>
    <circle cx="102" cy="93" r="5" fill="#D7DCEF"/>
    <g className="justice-balance"><path d="M55 115L149 105M63 114L48 148H80L63 114M140 107L124 142H156L140 107"/><path d="M48 148Q64 168 80 148M124 142Q140 162 156 142" fill="#8993C7" fillOpacity=".25"/></g>
   </g>
   <g className="justice-base"><ellipse cx="251" cy="231" rx="64" ry="10" fill="#9A684A"/><rect x="187" y="218" width="128" height="13" rx="5" fill="#C09066"/><ellipse cx="251" cy="218" rx="64" ry="10" fill="#E7BC8C"/><ellipse cx="251" cy="217" rx="47" ry="6" stroke="#C79464" strokeWidth="2"/></g>
   <g className="justice-impact" stroke="#FFD6A0" strokeWidth="3" strokeLinecap="round"><path d="M199 196L190 185M282 192L293 181M241 185V174"/><ellipse cx="249" cy="217" rx="74" ry="16" strokeWidth="1.5"/></g>
   <g className="justice-gavel">
    <path d="M243 139L332 201" stroke="#9A6547" strokeWidth="19" strokeLinecap="round"/>
    <path d="M244 136L333 198" stroke="url(#gavel-metal)" strokeWidth="13" strokeLinecap="round"/>
    <rect x="209" y="92" width="58" height="83" rx="10" fill="url(#gavel-metal)" transform="rotate(34 238 133)"/>
    <path d="M228 94L274 125M200 134L247 165" stroke="#FBE0BB" strokeWidth="5"/>
    <path d="M213 114L261 146" stroke="#A87147" strokeWidth="2" opacity=".55"/>
   </g>
   <g className="justice-sparks" fill="#F1B7C7"><circle cx="170" cy="62" r="3"/><circle cx="462" cy="141" r="3"/><path d="M302 48V60M296 54H308" stroke="#D1D7F3" strokeWidth="2" strokeLinecap="round"/></g>
  </svg>
 </div>;
}
