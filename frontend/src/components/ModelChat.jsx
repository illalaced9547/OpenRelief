import {useEffect,useRef,useState} from 'react';
import {ArrowUp,MessageCircle,X,Plus} from 'lucide-react';
import {demoAnswer} from '../data/explanations';
import {PHASE_LABEL,ENDPOINT,fetchLive,liveFor,SNAPSHOT_META} from '../lib/liveModel';

const snapshotDate = SNAPSHOT_META.generatedAt?.slice(0,16).replace('T',' ')+' UTC';

function modelAnswer(question,live,fromSnapshot){
 const q=question.toLowerCase();
 const phase=live.predicted_phase;
 const label=phase?`${phase} (${PHASE_LABEL[phase]})`:'unavailable (model output did not parse as valid JSON)';
 const provenance=fromSnapshot?`cached batch snapshot from ${snapshotDate} (saved historical model output)`:'a live call to the checkpoint, just now';
 if(/confiden|certain|sure|accur|reliab/.test(q))return `This checkpoint emits a categorical IPC phase plus rationale, not a calibrated confidence score. Predicted phase: ${label}.`;
 if(/source|where.*data|evidence|provenance/.test(q))return `Forecast for ${live.country}: cutoff ${live.cutoff}, target month ${live.target_month}, held-out test sample ${live.sample_id}. This is one of ${live.num_examples_for_country} prepared test examples for this country, from ${provenance}.`;
 if(/price|cost|wheat/.test(q))return `This model predicts FEWS NET IPC phase from time-series evidence; it does not output a price series. Predicted phase for ${live.country}: ${label}.`;
 if(!live.valid_output)return `The model's output for ${live.country} did not parse as valid JSON. Raw output: "${live.raw_output.slice(0,200)}${live.raw_output.length>200?'…':''}"`;
 const actions=live.recommended_actions?.length?` Recommended follow-up: ${live.recommended_actions.join('; ')}.`:'';
 return `Model forecast for ${live.country} (cutoff ${live.cutoff} → target ${live.target_month}): predicted IPC phase ${label}. ${live.rationale}${actions}`;
}

export default function ModelChat({context,open,onOpen,onClose,hidden=false}){
 const [draft,setDraft]=useState(''),[messages,setMessages]=useState([]),[pending,setPending]=useState(false);
 const end=useRef(null),input=useRef(null),launcher=useRef(null);
 useEffect(()=>{if(open&&!hidden){const timer=setTimeout(()=>input.current?.focus({preventScroll:true}),220);return()=>clearTimeout(timer)}},[open,hidden]);
 useEffect(()=>{if(open)end.current?.scrollIntoView({block:'nearest'})},[messages,open,pending]);
 const close=()=>{onClose();launcher.current?.focus({preventScroll:true})};
 const canGoLive=!!(context.iso3&&ENDPOINT);
 const hasSnapshot=!!liveFor(context.iso3);
 const send=async(question=draft)=>{
  const text=question.trim();if(!text||pending)return;
  const snapshot={...context};
  const stored=liveFor(snapshot.iso3);
  const label=stored?`${context.country} · Target ${stored.target_month}`:`${context.country} · ${context.horizon} days demo`;
  setMessages(m=>[...m,{role:'user',text,context:label}]);setDraft('');input.current?.focus();
  if(snapshot.iso3&&ENDPOINT){
   setPending(true);
   const live=await fetchLive(snapshot.iso3);
   setPending(false);
   if(live){setMessages(m=>[...m,{role:'assistant',text:modelAnswer(text,live,false),context:label,live:true}]);return}
   const cached=liveFor(snapshot.iso3);
   if(cached){setMessages(m=>[...m,{role:'assistant',text:modelAnswer(text,cached,true),context:label,live:true}]);return}
   setMessages(m=>[...m,{role:'assistant',text:demoAnswer(text,snapshot),context:label,live:false}]);
   return;
  }
  const cached=liveFor(snapshot.iso3);
  setMessages(m=>[...m,{role:'assistant',text:cached?modelAnswer(text,cached,true):demoAnswer(text,snapshot),context:label,live:!!cached}]);
 };
 return <><button ref={launcher} className="chat-launcher chat-icon" hidden={hidden} aria-label={open?"Close Ask OpenRelief":"Ask OpenRelief"} title={open?"Back to country overview":"Ask OpenRelief"} aria-controls="openrelief-chat" aria-expanded={open} onClick={()=>open?close():onOpen()}>{open?<X size={22}/>:<MessageCircle size={22}/>}</button><section id="openrelief-chat" className={`model-chat panel-chat ${open&&!hidden?'chat-visible':''}`} inert={!open||hidden} aria-hidden={!open||hidden} role="dialog" aria-label="Ask about the data" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close()}}}><div className="chat-heading"><div><MessageCircle size={18}/><strong>Ask OpenRelief</strong></div><div><button aria-label="New conversation" onClick={()=>{setMessages([]);setDraft('');input.current?.focus()}}><Plus size={18}/></button><button aria-label="Close chat" onClick={close}><X size={18}/></button></div></div><div className="chat-context"><i/>{context.country} <span>· {hasSnapshot?`Historical target ${liveFor(context.iso3).target_month}`:`Next ${context.horizon} days · Demo`}</span>{(canGoLive||hasSnapshot)&&<span className="live-pill"> · MODEL FORECAST AVAILABLE</span>}</div><div className="chat-messages" role="log" aria-live="polite">{!messages.length&&<div className="chat-welcome"><h3>Look beyond the number.</h3><p>{(canGoLive||hasSnapshot)?'Explore this country’s historical model forecast. Questions select explanations locally; the prediction endpoint receives only the country code.':'Explore the price movement, possible explanations and the evidence behind this country’s outlook.'}</p><div className="chat-prompts">{['Why this prediction?','How confident is it?','What are the sources?'].map(q=><button key={q} onClick={()=>send(q)}>{q}<ArrowUp size={13}/></button>)}</div></div>}{messages.map((m,i)=><div className={`chat-message ${m.role}`} key={i}><small>{m.role==='user'?'YOU':m.live?'MODEL FORECAST':'DEMO RESPONSE'} · {m.context}</small><p>{m.text}</p></div>)}{pending&&<div className="chat-message assistant"><small>MODEL FORECAST · running inference…</small><p>Calling the fine-tuned checkpoint on Nebius, this can take a few seconds…</p></div>}<div ref={end}/></div><div className="chat-disclaimer">{canGoLive?'Live checkpoint call · falls back to a cached snapshot, then demo answers, if unreachable':hasSnapshot?`Cached batch snapshot (${snapshotDate}) · live endpoint not configured`:'Demo answers · LLM not connected · No messages sent externally'}</div><form className="chat-input" onSubmit={e=>{e.preventDefault();send()}}><input ref={input} value={draft} onChange={e=>setDraft(e.target.value)} maxLength={2000} aria-label="Question about the data" placeholder="Ask about this prediction…"/><button type="submit" disabled={!draft.trim()||pending} aria-label="Send question"><ArrowUp size={18}/></button></form></section></>;
}
