import {useContext,useEffect,useId,useLayoutEffect,useRef,useState,type KeyboardEvent} from 'react';
import {createPortal} from 'react-dom';
import {CalendarDays,ChevronLeft,ChevronRight} from 'lucide-react';
import {FieldLabelContext} from './Dropdown';

const iso=(date:Date)=>[date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');
const parse=(value:string)=>{const [y,m,d]=value.split('-').map(Number);return y&&m&&d?new Date(y,m-1,d,12):new Date()};
const shiftMonth=(date:Date,step:number)=>new Date(date.getFullYear(),date.getMonth()+step,Math.min(date.getDate(),new Date(date.getFullYear(),date.getMonth()+step+1,0).getDate()),12);
export function DatePicker({value,onChange}:{value:string;onChange:(value:string)=>void}){
 const label=useContext(FieldLabelContext)||'Tanggal',id=useId(),[open,setOpen]=useState(false),[cursor,setCursor]=useState(()=>parse(value));
 const trigger=useRef<HTMLButtonElement>(null),dialog=useRef<HTMLDialogElement>(null);
 const [position,setPosition]=useState({left:8,top:8});
 const start=new Date(cursor.getFullYear(),cursor.getMonth(),1,12);start.setDate(start.getDate()-(start.getDay()+6)%7);
 const days=Array.from({length:42},(_,index)=>new Date(start.getFullYear(),start.getMonth(),start.getDate()+index,12));
 const close=()=>setOpen(false);
 const choose=(date:Date)=>{onChange(iso(date));close()};
 useLayoutEffect(()=>{
  if(!open)return;
  const place=()=>{const bounds=trigger.current?.getBoundingClientRect(),sheet=dialog.current;if(!bounds||!sheet)return;const width=Math.min(324,window.innerWidth-20),height=sheet.getBoundingClientRect().height;const bottom=window.visualViewport?.height??window.innerHeight;const above=bounds.top-height-8;setPosition({left:Math.max(10,Math.min(bounds.left,window.innerWidth-width-10)),top:bounds.bottom+height+8>bottom&&above>=10?above:Math.max(10,Math.min(bounds.bottom+8,bottom-height-10))})};
  const sheet=dialog.current;if(!sheet?.open)sheet?.showModal();place();
  window.addEventListener('resize',place);window.visualViewport?.addEventListener('resize',place);
  return()=>{sheet?.close();window.removeEventListener('resize',place);window.visualViewport?.removeEventListener('resize',place)};
 },[open]);
 useEffect(()=>{if(open)dialog.current?.querySelector<HTMLButtonElement>('[data-cursor="true"]')?.focus({preventScroll:true})},[open,cursor]);
 const move=(event:KeyboardEvent)=>{let next=new Date(cursor);const day=next.getDay();if(event.key==='ArrowLeft')next.setDate(next.getDate()-1);else if(event.key==='ArrowRight')next.setDate(next.getDate()+1);else if(event.key==='ArrowUp')next.setDate(next.getDate()-7);else if(event.key==='ArrowDown')next.setDate(next.getDate()+7);else if(event.key==='Home')next.setDate(next.getDate()-(day+6)%7);else if(event.key==='End')next.setDate(next.getDate()+6-(day+6)%7);else if(event.key==='PageUp')next=shiftMonth(next,-1);else if(event.key==='PageDown')next=shiftMonth(next,1);else return;event.preventDefault();setCursor(next)};
 return <><button ref={trigger} className="sipak-date-trigger" type="button" aria-label={label} aria-haspopup="dialog" aria-expanded={open} aria-controls={open?id:undefined} onClick={()=>{setCursor(parse(value));setOpen(true)}}><span>{value?parse(value).toLocaleDateString('id-ID',{day:'numeric',month:'long',year:'numeric'}):'Pilih tanggal'}</span><CalendarDays size={18}/></button>
  {open&&createPortal(<dialog ref={dialog} id={id} className="sipak-date-dialog" aria-label={'Pilih '+label.toLocaleLowerCase()} style={position} onCancel={close} onClick={event=>{if(event.target===event.currentTarget){const b=event.currentTarget.getBoundingClientRect();if(event.clientX<b.left||event.clientX>b.right||event.clientY<b.top||event.clientY>b.bottom)close()}}}>
   <header><button type="button" aria-label="Bulan sebelumnya" onClick={()=>setCursor(shiftMonth(cursor,-1))}><ChevronLeft size={18}/></button><strong aria-live="polite">{cursor.toLocaleDateString('id-ID',{month:'long',year:'numeric'})}</strong><button type="button" aria-label="Bulan berikutnya" onClick={()=>setCursor(shiftMonth(cursor,1))}><ChevronRight size={18}/></button></header>
   <div role="grid" aria-label={cursor.toLocaleDateString('id-ID',{month:'long',year:'numeric'})} onKeyDown={move}><div className="calendar-week" role="row">{['Sen','Sel','Rab','Kam','Jum','Sab','Min'].map(day=><span role="columnheader" key={day}>{day}</span>)}</div>{Array.from({length:6},(_,week)=><div className="calendar-week" role="row" key={week}>{days.slice(week*7,week*7+7).map(day=><div role="gridcell" key={iso(day)} aria-selected={value===iso(day)}><button type="button" tabIndex={iso(day)===iso(cursor)?0:-1} data-cursor={iso(day)===iso(cursor)} className={(day.getMonth()!==cursor.getMonth()?'outside-month ':'')+(iso(day)===iso(new Date())?'is-today':'')} aria-label={day.toLocaleDateString('id-ID',{weekday:'long',day:'numeric',month:'long',year:'numeric'})} aria-current={iso(day)===iso(new Date())?'date':undefined} onClick={()=>choose(day)}>{day.getDate()}</button></div>)}</div>)}</div>
   <footer><button type="button" onClick={()=>{onChange('');close()}}>Kosongkan</button><button type="button" onClick={()=>choose(new Date())}>Hari ini</button></footer>
  </dialog>,document.body)}
 </>;
}
