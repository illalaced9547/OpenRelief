import {useEffect,useRef,useState} from 'react';
import {ArrowUp,MessageCircle,X,Plus} from 'lucide-react';
import {demoAnswer} from '../data/explanations';

const ENDPOINT = import.meta.env.VITE_INFERENCE_URL;
const PHASE_LABEL = {1:'Minimal',2:'Stressed',3:'Crisis',4:'Emergency',5:'Famine'};
const liveCache = {};

// Live prediction is a real forward pass through the fine-tuned checkpoint on a
// held-out test-partition example for this country (see src/open_relief/serve.py) -
// not a free-form query. Cached per iso3 so re-asking a question in the same
// session does not re-run generation.
async function fetchLive(iso3){
 if(!ENDPOINT||!iso3)return null;
 if(liveCache[iso3])return liveCache[iso3];
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),25000);
 try{
  const res=await fetch(`${ENDPOINT}/predict?iso3=${iso3}`,{signal:controller.signal});
  if(!res.ok)throw new Error(`inference endpoint returned ${res.status}`);
  const data=await res.json();
  liveCache[iso3]=data;
  return data;
 }catch(err){
  console.warn('Live model call failed, falling back to demo answers:',err);
  return null;
 }finally{
  clearTimeout(timeout);
 }
}

function liveAnswer(question,live){
 const q=question.toLowerCase();
 const phase=live.predicted_phase;
 const label=phase?`${phase} (${PHASE_LABEL[phase]})`:'unavailable (model output did not parse as valid JSON)';
 if(/confiden|certain|sure|accur|reliab/.test(q))return `This checkpoint emits a categorical IPC phase plus rationale, not a calibrated confidence score. Predicted phase: ${label}.`;
 if(/source|where.*data|evidence|provenance/.test(q))return `Live forecast for ${live.country}: cutoff ${live.cutoff}, target month ${live.target_month}, held-out test sample ${live.sample_id}. This is one of ${live.num_examples_for_country} prepared test examples for this country, run through the fine-tuned checkpoint just now.`;
 if(/price|cost|wheat/.test(q))return `This model predicts FEWS NET IPC phase from time-series evidence; it does not output a price series. Predicted phase for ${live.country}: ${label}.`;
 if(!live.valid_output)return `The live model call for ${live.country} did not return parseable JSON. Raw output: "${live.raw_output.slice(0,200)}${live.raw_output.length>200?'…':''}"`;
 const actions=live.recommended_actions?.length?` Recommended follow-up: ${live.recommended_actions.join('; ')}.`:'';
 return `Live model forecast for ${live.country} (cutoff ${live.cutoff} → target ${live.target_month}): predicted IPC phase ${label}. ${live.rationale}${actions}`;
}

export default function ModelChat({context,open,onOpen,onClose,hidden=false}){
 const [draft,setDraft]=useState(''),[messages,setMessages]=useState([]),[pending,setPending]=useState(false);
 const end=useRef(null),input=useRef(null),launcher=useRef(null);
 useEffect(()=>{if(open&&!hidden){const timer=setTimeout(()=>input.current?.focus({preventScroll:true}),220);return()=>clearTimeout(timer)}},[open,hidden]);
 useEffect(()=>{if(open)end.current?.scrollIntoView({block:'nearest'})},[messages,open,pending]);
 const close=()=>{onClose();launcher.current?.focus({preventScroll:true})};
 const send=async(question=draft)=>{
  const text=question.trim();if(!text||pending)return;
  const snapshot={...context};
  const label=`${context.country} · ${context.horizon} days`;
  setMessages(m=>[...m,{role:'user',text,context:label}]);setDraft('');input.current?.focus();
  if(snapshot.iso3&&ENDPOINT){
   setPending(true);
   const live=await fetchLive(snapshot.iso3);
   setPending(false);
   setMessages(m=>[...m,{role:'assistant',text:live?liveAnswer(text,live):demoAnswer(text,snapshot),context:label,live:!!live}]);
   return;
  }
  setMessages(m=>[...m,{role:'assistant',text:demoAnswer(text,snapshot),context:label,live:false}]);
 };
 const canGoLive=!!(context.iso3&&ENDPOINT);
 return <><button ref={launcher} className="chat-launcher chat-icon" hidden={hidden} aria-label={open?"Close Ask OpenRelief":"Ask OpenRelief"} title={open?"Back to country overview":"Ask OpenRelief"} aria-controls="openrelief-chat" aria-expanded={open} onClick={()=>open?close():onOpen()}>{open?<X size={22}/>:<MessageCircle size={22}/>}</button><section id="openrelief-chat" className={`model-chat panel-chat ${open&&!hidden?'chat-visible':''}`} inert={!open||hidden} aria-hidden={!open||hidden} role="dialog" aria-label="Ask about the data" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close()}}}><div className="chat-heading"><div><MessageCircle size={18}/><strong>Ask OpenRelief</strong></div><div><button aria-label="New conversation" onClick={()=>{setMessages([]);setDraft('');input.current?.focus()}}><Plus size={18}/></button><button aria-label="Close chat" onClick={close}><X size={18}/></button></div></div><div className="chat-context"><i/>{context.country} <span>· Next {context.horizon} days</span>{canGoLive&&<span className="live-pill"> · LIVE MODEL AVAILABLE</span>}</div><div className="chat-messages" role="log" aria-live="polite">{!messages.length&&<div className="chat-welcome"><h3>Look beyond the number.</h3><p>{canGoLive?'Ask the fine-tuned checkpoint about this country’s held-out forecast.':'Explore the price movement, possible explanations and the evidence behind this country’s outlook.'}</p><div className="chat-prompts">{['Why this prediction?','How confident is it?','What are the sources?'].map(q=><button key={q} onClick={()=>send(q)}>{q}<ArrowUp size={13}/></button>)}</div></div>}{messages.map((m,i)=><div className={`chat-message ${m.role}`} key={i}><small>{m.role==='user'?'YOU':m.live?'LIVE MODEL':'DEMO RESPONSE'} · {m.context}</small><p>{m.text}</p></div>)}{pending&&<div className="chat-message assistant"><small>LIVE MODEL · running inference…</small><p>Consulting the fine-tuned checkpoint on Nebius, this can take a few seconds…</p></div>}<div ref={end}/></div><div className="chat-disclaimer">{canGoLive?'Live checkpoint on a held-out test example · Falls back to demo answers if the model is unreachable':'Demo answers · LLM not connected · No messages sent externally'}</div><form className="chat-input" onSubmit={e=>{e.preventDefault();send()}}><input ref={input} value={draft} onChange={e=>setDraft(e.target.value)} maxLength={2000} aria-label="Question about the data" placeholder="Ask about this prediction…"/><button type="submit" disabled={!draft.trim()||pending} aria-label="Send question"><ArrowUp size={18}/></button></form></section></>;
}
