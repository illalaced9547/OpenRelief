import {useEffect,useRef,useState} from 'react';
import {ArrowUp,MessageCircle,X,Plus} from 'lucide-react';
import {demoAnswer} from '../data/explanations';
export default function ModelChat({context,open,onOpen,onClose,hidden=false}){
 const [draft,setDraft]=useState(''),[messages,setMessages]=useState([]);
 const end=useRef(null),input=useRef(null),launcher=useRef(null);
 useEffect(()=>{if(open&&!hidden){const timer=setTimeout(()=>input.current?.focus({preventScroll:true}),220);return()=>clearTimeout(timer)}},[open,hidden]);
 useEffect(()=>{if(open)end.current?.scrollIntoView({block:'nearest'})},[messages,open]);
 const close=()=>{onClose();launcher.current?.focus({preventScroll:true})};
 const send=(question=draft)=>{
  const text=question.trim();if(!text)return;
  const snapshot={...context};
  setMessages(m=>[...m,{role:'user',text,context:`${context.country} · ${context.horizon} days`},{role:'assistant',text:demoAnswer(text,snapshot),context:`${context.country} · ${context.horizon} days`}]);setDraft('');input.current?.focus();
 };
 return <><button ref={launcher} className="chat-launcher chat-icon" hidden={hidden} aria-label={open?"Close Ask OpenRelief":"Ask OpenRelief"} title={open?"Back to country overview":"Ask OpenRelief"} aria-controls="openrelief-chat" aria-expanded={open} onClick={()=>open?close():onOpen()}>{open?<X size={22}/>:<MessageCircle size={22}/>}</button><section id="openrelief-chat" className={`model-chat panel-chat ${open&&!hidden?'chat-visible':''}`} inert={!open||hidden} aria-hidden={!open||hidden} role="dialog" aria-label="Ask about the data" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close()}}}><div className="chat-heading"><div><MessageCircle size={18}/><strong>Ask OpenRelief</strong></div><div><button aria-label="New conversation" onClick={()=>{setMessages([]);setDraft('');input.current?.focus()}}><Plus size={18}/></button><button aria-label="Close chat" onClick={close}><X size={18}/></button></div></div><div className="chat-context"><i/>{context.country} <span>· Next {context.horizon} days</span></div><div className="chat-messages" role="log" aria-live="polite">{!messages.length&&<div className="chat-welcome"><h3>Look beyond the number.</h3><p>Explore the price movement, possible explanations and the evidence behind this country’s outlook.</p><div className="chat-prompts">{['Why this prediction?','How confident is it?','What are the sources?'].map(q=><button key={q} onClick={()=>send(q)}>{q}<ArrowUp size={13}/></button>)}</div></div>}{messages.map((m,i)=><div className={`chat-message ${m.role}`} key={i}><small>{m.role==='user'?'YOU':'DEMO RESPONSE'} · {m.context}</small><p>{m.text}</p></div>)}<div ref={end}/></div><div className="chat-disclaimer">Demo answers · LLM not connected · No messages sent externally</div><form className="chat-input" onSubmit={e=>{e.preventDefault();send()}}><input ref={input} value={draft} onChange={e=>setDraft(e.target.value)} maxLength={2000} aria-label="Question about the data" placeholder="Ask about this prediction…"/><button type="submit" disabled={!draft.trim()} aria-label="Send question"><ArrowUp size={18}/></button></form></section></>;
}
