import {ArrowRight,Globe2,Info} from 'lucide-react';
import {PHASE_LABEL,phaseColor,snapshotMeta,formatDate} from '../data/modelData';

export default function CountryDetails({country,name,tab,setTab,hidden}){
 return <aside className={`country-panel explanation-panel ${hidden?'panel-away':''}`} inert={hidden} aria-hidden={hidden}>
  <div className="panel-eyebrow">MODEL OUTLOOK <span className="demo-pill">{country?'SAVED PREDICTION':'NO MODEL DATA'}</span></div>
  <div className="country-heading"><h3>{name}</h3></div>
  <p className="region">{country?'One historical district sample · Country location only':'No prediction supplied for this country'}</p>
  {!country?<div className="empty-state"><Globe2 size={28}/><p>Choose a colored country to view its model result. Countries without an output have no estimated score.</p></div>:<>
   <div className="detail-tabs" role="group" aria-label="Country detail view">{[['outlook','Outlook'],['explanation','Explanation'],['sources','Sources']].map(([id,label])=><button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}>{label}</button>)}</div>
   <div className="detail-content">
    {tab==='outlook'?<>
     <div className="probability"><span>{country.phase??'—'}<small>/5</small></span><span className="risk-badge" style={{color:phaseColor(country.phase),background:phaseColor(country.phase)+'26'}}>{PHASE_LABEL[country.phase]||'Unavailable'}</span></div>
     <p className="probability-label">Predicted FEWS NET IPC severity phase<br/>Target {country.target_month} · Three months after cutoff</p>
     <div className="phase-scale" aria-label={`Predicted IPC phase ${country.phase??'unavailable'}`}>{[1,2,3,4,5].map(n=><span key={n} style={{background:phaseColor(n),opacity:country.phase===n?1:.25}}>{n}</span>)}</div>
     <div className="confidence-card"><div><span>Prediction confidence</span><strong>Not provided</strong></div><p>The model returns a severity class, not a calibrated probability or confidence percentage.</p></div>
     <div className="source-row"><span>Input cutoff</span><small>{formatDate(country.cutoff)}</small></div>
     <div className="source-row"><span>Last known IPC phase</span><small>{country.baseline_phase??'Unavailable'}</small></div>
     <button className="explanation-preview" onClick={()=>setTab('explanation')}><span>Why this prediction?</span><strong>Read the model’s generated rationale</strong><ArrowRight size={16}/></button>
    </>:tab==='explanation'?<>
     <span className="section-kicker">GENERATED MODEL RATIONALE</span><h4>{PHASE_LABEL[country.phase]||'Unparsed output'} · Target {country.target_month}</h4>
     <p>{country.valid_output?country.rationale:country.raw_output||'No explanation returned.'}</p>
     {!!country.recommended_actions?.length&&<><span className="section-kicker">MODEL-SUGGESTED FOLLOW-UP</span>{country.recommended_actions.map((action,i)=><p key={i}>{action}</p>)}</>}
     <div className="uncertainty-note"><Info size={15}/><p>Generated explanations can contain errors. They are hypotheses, not evidence of causation. This is a historical district sample, not a current nationwide assessment.</p></div>
    </>:<>
     <span className="section-kicker">PREDICTION PROVENANCE</span>
     {[['Sample ID',country.sample_id],['Input cutoff',formatDate(country.cutoff)],['Target month',country.target_month],['Test examples in this country',country.num_examples_for_country],['Snapshot generated',formatDate(snapshotMeta.generatedAt)]].map(([label,value])=><div className="source-row" key={label}><span>{label}</span><small>{value}</small></div>)}
     <div className="source-metadata"><span>Checkpoint <strong>{snapshotMeta.checkpoint}</strong></span></div>
     <p>The pipeline uses food-security history, PortWatch shipping, ACLED conflict, CHIRPS rainfall and WFP staple prices. Individual source observations and URLs are not included in this prediction response.</p>
     <a className="model-source-link" href="https://github.com/luk-huebner/OpenRelief/blob/main/docs/SOURCES.md" target="_blank" rel="noreferrer">View the pipeline source inventory ↗</a>
    </>}
   </div>
  </>}
 </aside>;
}
