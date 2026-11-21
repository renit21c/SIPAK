import {Children,createContext,isValidElement,useContext,useEffect,useId,useLayoutEffect,useMemo,useRef,useState,type KeyboardEvent,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {Check,ChevronDown} from 'lucide-react';

export const FieldLabelContext=createContext('');
type Option={value:string;label:string;disabled:boolean};
function textOf(node:ReactNode):string{return Children.toArray(node).map(child=>isValidElement<{children?:ReactNode}>(child)?textOf(child.props.children):String(child)).join('')}
function optionsOf(children:ReactNode):Option[]{return Children.toArray(children).flatMap(child=>{
 if(!isValidElement<{value?:string;children?:ReactNode;disabled?:boolean}>(child))return [];
 if(child.type==='option')return [{value:String(child.props.value??textOf(child.props.children)),label:textOf(child.props.children),disabled:!!child.props.disabled}];
 return optionsOf(child.props.children);
})}

export function Dropdown({value,onChange,children,label,disabled=false,required=false,editable=false,placeholder,name}:{value:string;onChange:(value:string)=>void;children:ReactNode;label?:string;disabled?:boolean;required?:boolean;editable?:boolean;placeholder?:string;name?:string}){
 const fieldLabel=useContext(FieldLabelContext),id=useId();
 const options=useMemo(()=>optionsOf(children),[children]);
 const [open,setOpen]=useState(false),[active,setActive]=useState(-1),[invalid,setInvalid]=useState(false);
 const [position,setPosition]=useState({left:0,top:0,width:0,maxHeight:280});
 const anchor=useRef<HTMLDivElement>(null),trigger=useRef<HTMLButtonElement|HTMLInputElement|null>(null),list=useRef<HTMLDivElement>(null),typeahead=useRef({text:'',time:0});
 const shown=editable?options.filter(option=>(option.value+' '+option.label).toLocaleLowerCase().includes(value.toLocaleLowerCase())):options;
 const selected=options.find(option=>option.value===value),accessibleLabel=label||fieldLabel;
 const close=()=>setOpen(false);
 const choose=(option:Option)=>{if(option.disabled)return;onChange(option.value);setInvalid(false);close();trigger.current?.focus()};
 const reveal=(last=false)=>{if(disabled)return;const selectedIndex=shown.findIndex(option=>option.value===value&&!option.disabled);setActive(selectedIndex>=0?selectedIndex:last?shown.map((option,index)=>option.disabled?-1:index).filter(index=>index>=0).pop()??-1:shown.findIndex(option=>!option.disabled));setOpen(true)};
 useEffect(()=>{if(disabled)close()},[disabled]);
 useLayoutEffect(()=>{
  if(!open)return;
  const place=()=>{const rect=anchor.current?.getBoundingClientRect();if(!rect)return;const viewport=window.visualViewport;const bottom=(viewport?.height??window.innerHeight)+(viewport?.offsetTop??0);const above=rect.top-12,below=bottom-rect.bottom-12;const up=below<180&&above>below;const maxHeight=Math.max(44,Math.min(280,up?above:below));const width=Math.min(Math.max(rect.width,200),window.innerWidth-16);const height=Math.min(maxHeight,list.current?.scrollHeight||48);setPosition({left:Math.max(8,Math.min(rect.left,window.innerWidth-width-8)),top:up?rect.top-height-6:rect.bottom+6,width,maxHeight})};
  place();window.addEventListener('resize',place);window.addEventListener('scroll',place,true);window.visualViewport?.addEventListener('resize',place);
  const outside=(event:PointerEvent)=>{if(!anchor.current?.contains(event.target as Node)&&!list.current?.contains(event.target as Node))close()};
  document.addEventListener('pointerdown',outside);
  return()=>{window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);window.visualViewport?.removeEventListener('resize',place);document.removeEventListener('pointerdown',outside)};
 },[open,shown.length,position.width]);
 useEffect(()=>{if(open)list.current?.querySelector('[data-highlighted="true"]')?.scrollIntoView({block:'nearest'})},[open,active]);
 const keyDown=(event:KeyboardEvent)=>{
  if(event.key==='Escape'){if(open){event.preventDefault();event.stopPropagation();close()}return}
  if(event.key==='Tab'){close();return}
  if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)&&(!editable||open||event.key.startsWith('Arrow'))){event.preventDefault();if(!open){reveal(event.key==='ArrowUp'||event.key==='End');return}let next=event.key==='Home'?0:event.key==='End'?shown.length-1:active+(event.key==='ArrowDown'?1:-1);const step=event.key==='ArrowUp'||event.key==='End'?-1:1;while(next>=0&&next<shown.length&&shown[next].disabled)next+=step;if(next>=0&&next<shown.length)setActive(next);return}
  if(event.key==='Enter'||(!editable&&event.key===' ')){event.preventDefault();if(open&&shown[active])choose(shown[active]);else if(!open)reveal();return}
  if(!editable&&event.key.length===1&&!event.ctrlKey&&!event.metaKey&&!event.altKey){event.preventDefault();const now=Date.now();const previous=now-typeahead.current.time<700?typeahead.current.text:'';const query=previous===event.key?'':previous;typeahead.current={text:query+event.key.toLocaleLowerCase(),time:now};const index=shown.findIndex(option=>!option.disabled&&option.label.toLocaleLowerCase().startsWith(typeahead.current.text));if(index>=0){setActive(index);setOpen(true)}}
 };
 const aria={'aria-label':accessibleLabel,'aria-expanded':open,'aria-controls':open?id:undefined,'aria-activedescendant':open&&shown[active]?id+'-'+active:undefined,'aria-required':required||undefined,'aria-invalid':invalid||undefined};
 return <div ref={anchor} className={'sipak-select'+(open?' is-open':'')+(disabled?' is-disabled':'')} onBlur={event=>{if(!event.currentTarget.contains(event.relatedTarget as Node))close()}}>
  {editable?<input {...aria} ref={node=>{trigger.current=node}} role="combobox" aria-autocomplete="list" value={value} disabled={disabled} placeholder={placeholder} autoComplete="off" className="sipak-select-trigger" onChange={event=>{onChange(event.target.value);setActive(-1);setOpen(true);setInvalid(false)}} onFocus={()=>reveal()} onClick={()=>{if(!open)reveal()}} onKeyDown={keyDown}/>:<button {...aria} ref={node=>{trigger.current=node}} type="button" role="combobox" aria-haspopup="listbox" disabled={disabled} className="sipak-select-trigger" onClick={()=>open?close():reveal()} onKeyDown={keyDown}><span>{selected?.label||placeholder||'Pilih…'}</span></button>}
  <ChevronDown className="sipak-select-chevron" size={17} aria-hidden="true"/>
  <input className="sipak-select-validation" aria-hidden="true" tabIndex={-1} name={name} value={value} required={required} disabled={disabled} onChange={()=>{}} onInvalid={event=>{event.preventDefault();setInvalid(true);trigger.current?.focus()}}/>
  {open&&createPortal(<div ref={list} id={id} role="listbox" aria-label={accessibleLabel} className="sipak-select-menu" style={position} onPointerDown={event=>event.preventDefault()}>
   {shown.length?shown.map((option,index)=><div key={option.value} id={id+'-'+index} role="option" aria-selected={option.value===value} aria-disabled={option.disabled||undefined} data-highlighted={index===active} className="sipak-select-option" onPointerMove={()=>{if(!option.disabled)setActive(index)}} onClick={()=>choose(option)}><span>{option.label}</span>{option.value===value&&<Check size={17} aria-hidden="true"/>}</div>):<div className="sipak-select-empty">{editable?'Ketik ID model pilihanmu':'Tidak ada pilihan'}</div>}
  </div>,document.body)}
 </div>;
}
