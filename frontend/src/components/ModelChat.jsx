import {useEffect,useRef,useState} from 'react';
import {ArrowUp,MessageCircle,X,Plus} from 'lucide-react';
import {ENDPOINT,fetchLive,liveFor} from '../lib/liveModel';
import {PHASE_LABEL,snapshotMeta,formatDate} from '../data/modelData';

function modelAnswer(question,prediction){
 const q=question.toLowerCase(),phase=prediction.predicted_phase;
 const label=prediction.valid_output&&phase?`${phase} (${PHASE_LABEL[phase]})`:'unavailable';
 if(/confiden|certain|sure|accur|reliab|probabil/.test(q))return `Predicted IPC phase: ${label}. The checkpoint does not provide calibrated confidence or a probability of hunger. Phase 1–5 is a severity classification, not a percentage.`;
 if(/source|where.*data|evidence|provenance/.test(q))return `Historical sample ${prediction.sample_id} for ${prediction.country}. Input cutoff: ${formatDate(prediction.cutoff)}; target month: ${prediction.target_month}. The pipeline uses food-security history, shipping, conflict, rainfall and staple-price series. This response does not include the individual source observations. The country represents one district example, not a national forecast.`;
 if(/price|cost|wheat/.test(q))return `The model response does not include a price series or current market prices. It predicts IPC phase ${label}. Any price statements in its rationale are generated claims about the historical input window and need source verification.`;
 if(!prediction.valid_output)return 'The model did not return a valid phase and explanation for this sample. No score or explanation has been estimated in its place.';
 if(/why|reason|explain|predict|outlook|rationale/.test(q))return `Target ${prediction.target_month}: predicted IPC phase ${label}. ${prediction.rationale}`;
 return 'The connected endpoint accepts a country code, not a free-form question. I can show its saved or freshly generated historical prediction, rationale, provenance, and uncertainty limits. Try “Why this prediction?” or “What are the sources?”';
}
export default function ModelChat({context,open,onOpen,onClose,hidden=false}){
 const [draft,setDraft]=useState(''),[messages,setMessages]=useState([]),[pending,setPending]=useState(false);
 const end=useRef(null),input=useRef(null),launcher=useRef(null);
 useEffect(()=>{if(open&&!hidden){const timer=setTimeout(()=>input.current?.focus({preventScroll:true}),220);return()=>clearTimeout(timer)}},[open,hidden]);
 useEffect(()=>{if(open)end.current?.scrollIntoView({block:'nearest'})},[messages,open,pending]);
 const close=()=>{onClose();launcher.current?.focus({preventScroll:true})};
 const stored=liveFor(context.iso3),canGoLive=!!(stored&&ENDPOINT);
 const send=async(question=draft)=>{
  const text=question.trim();if(!text||pending)return;
  const selected={...context},saved=liveFor(selected.iso3);
  const label=`${selected.country}${saved?` · Target ${saved.target_month}`:''}`;
  setMessages(m=>[...m,{role:'user',text,context:label}]);setDraft('');
  if(!saved){setMessages(m=>[...m,{role:'assistant',text:'No model output is available for this country. Choose a colored country on the map.',context:label,source:'NO MODEL DATA'}]);return}
  setPending(true);
  try{
   const live=ENDPOINT?await fetchLive(selected.iso3):null;
   const prediction=live||saved;
   const answer=modelAnswer(text,prediction);
   setMessages(m=>[...m,{role:'assistant',text:answer,context:label,source:live?'LIVE MODEL':'SAVED MODEL'}]);
  }finally{setPending(false)}
 };
 return <><button ref={launcher} className="chat-launcher chat-icon" hidden={hidden} aria-label={open?'Close Ask OpenRelief':'Ask OpenRelief'} aria-controls="openrelief-chat" aria-expanded={open} onClick={()=>open?close():onOpen()}>{open?<X size={22}/>:<MessageCircle size={22}/>}</button>
 <section id="openrelief-chat" className={`model-chat panel-chat ${open&&!hidden?'chat-visible':''}`} inert={!open||hidden} aria-hidden={!open||hidden} role="dialog" aria-label="Ask about the data" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close()}}}>
  <div className="chat-heading"><div><MessageCircle size={18}/><strong>Ask OpenRelief</strong></div><div><button aria-label="New conversation" disabled={pending} onClick={()=>{setMessages([]);setDraft('');input.current?.focus()}}><Plus size={18}/></button><button aria-label="Close chat" onClick={close}><X size={18}/></button></div></div>
  <div className="chat-context"><i/>{context.country}<span>{stored?` · Historical target ${stored.target_month}`:' · No model data'}</span></div>
  <div className="chat-messages" role="log" aria-live="polite">{!messages.length&&<div className="chat-welcome"><h3>Understand the prediction.</h3><p>{stored?'Explore the model’s phase, rationale and source limitations for this historical sample.':'Choose a country with model data to explore its prediction.'}</p>{stored&&<div className="chat-prompts">{['Why this prediction?','How confident is it?','What are the sources?'].map(q=><button disabled={pending} key={q} onClick={()=>send(q)}>{q}<ArrowUp size={13}/></button>)}</div>}</div>}{messages.map((m,i)=><div className={`chat-message ${m.role}`} key={i}><small>{m.role==='user'?'YOU':m.source} · {m.context}</small><p>{m.text}</p></div>)}{pending&&<div className="chat-message assistant chat-loading" role="status"><div className="chat-loading-label"><span className="chat-loading-dots" aria-hidden="true"><i/><i/><i/></span><span>Loading model response…</span></div><div className="chat-loading-lines" aria-hidden="true"><span/><span/><span/></div></div>}<div ref={end}/></div>
  <div className="chat-disclaimer">{canGoLive?'Answers from the trained model · Nebius inference · Saved output if unavailable':stored?`Saved trained-model output · ${formatDate(snapshotMeta.generatedAt)}`:'No model output for this country'}</div>
  <form className="chat-input" onSubmit={e=>{e.preventDefault();send()}}><input ref={input} value={draft} onChange={e=>setDraft(e.target.value)} maxLength={2000} aria-label="Question about the data" placeholder="Ask about this prediction…"/><button type="submit" disabled={!draft.trim()||pending} aria-label="Send question"><ArrowUp size={18}/></button></form>
 </section></>;
}
