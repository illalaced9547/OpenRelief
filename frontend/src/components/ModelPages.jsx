import {ArrowUpRight} from 'lucide-react';
import {modelEntries,PHASE_LABEL,phaseColor,snapshotMeta,formatDate} from '../data/modelData';

export function GlobalInsights({onExplore}){
 const counts=Object.keys(PHASE_LABEL).map(Number).map(phase=>({phase,count:modelEntries.filter(d=>d.phase===phase).length}));
 return <section className="model-page" aria-labelledby="insights-title"><div className="model-page-inner">
  <div className="model-page-heading"><span className="eyebrow">GLOBAL INSIGHTS</span><h1 id="insights-title">Inside the model’s outlook.</h1><p>Explore the same {modelEntries.length} saved predictions shown on the map. Each country represents one held-out district example; these are historical samples, not a global hunger estimate.</p><span className="demo-pill">SNAPSHOT · {formatDate(snapshotMeta.generatedAt)}</span></div>
  <div className="phase-summary">{counts.map(({phase,count})=><article key={phase}><span style={{color:phaseColor(phase)}}>IPC {phase} · {PHASE_LABEL[phase]}</span><strong>{count}</strong><small>sample{count===1?'':'s'}</small></article>)}</div>
  <div className="model-page-section-title"><h2>Explore each prediction</h2><span>Highest to lowest phase</span></div>
  <div className="model-result-grid">{[...modelEntries].sort((a,b)=>(b.phase??0)-(a.phase??0)||a.name.localeCompare(b.name)).map(d=><article className="model-result-card" key={d.id}><div className="model-card-meta"><span>Target {d.target_month}</span><span style={{color:phaseColor(d.phase)}}>IPC {d.phase??'—'} · {PHASE_LABEL[d.phase]||'Unavailable'}</span></div><h2>{d.name}</h2><p className="rationale-excerpt">{d.rationale||'No parsed rationale available.'}</p><button onClick={()=>onExplore(d.id)}>Read explanation on map <ArrowUpRight size={16}/></button></article>)}</div>
 </div></section>;
}

export function Roadmap(){
 const steps=[
  ['Available','Historical predictions',`${modelEntries.length} saved model outputs are connected to the map, with predicted IPC phases, generated rationales and sample provenance.`],
  ['Connected','On-demand inference','The chat can request a fresh forward pass for a stored country sample. If the GPU server is unavailable, it uses the saved prediction. Questions are interpreted locally; the server accepts country codes, not conversation.'],
  ['Next · not available','Current data and district coverage','Prepare current six-month input windows, retain district identifiers in the response, and publish dated forecasts. Current map shading represents one historical sample per country.'],
  ['Next · not available','Validated uncertainty and richer answers','Evaluate calibration before showing probabilities. Add source observations and a question-answering endpoint before offering price charts, confidence percentages or free-form model conversations.']
 ];
 return <section className="model-page" aria-labelledby="roadmap-title"><div className="model-page-inner"><div className="model-page-heading"><span className="eyebrow">ROADMAP</span><h1 id="roadmap-title">From historical evidence to live outlooks.</h1><p>What the connected system provides today, and what it still needs. Planned work has no committed release dates.</p></div><div className="model-roadmap-grid">{steps.map(([status,title,body],i)=><article key={title}><div className="model-card-meta"><span>0{i+1}</span><span>{status}</span></div><h2>{title}</h2><p>{body}</p></article>)}</div><p className="model-page-note">Current checkpoint: {snapshotMeta.checkpoint}. The website serves results; CUDA compute generates new model outputs.</p></div></section>;
}
