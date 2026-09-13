import {useRef,useState} from 'react';
import {ArrowUpRight} from 'lucide-react';
import examples from '../data/annotationExamples.json';
import {modelEntries,formatDate} from '../data/modelData';
import beniPng from '../assets/annotation-atlas/beni.png';
import oubritengaPng from '../assets/annotation-atlas/oubritenga.png';
import './AnnotationAtlas.css';
const images={beni:beniPng,oubritenga:oubritengaPng};
const repo='https://github.com/luk-huebner/OpenRelief/blob/main/docs/examples/annotation-atlas/';
export default function AnnotationAtlas({onExplore}){
 const [selected,setSelected]=useState(0),panel=useRef(null);
 const example=examples[selected],a=example.annotation;
 const country=modelEntries.find(d=>d.iso3===example.input.geography.iso3);
 const switchExample=index=>{setSelected(index);panel.current?.scrollTo({top:0})};
 return <section className="annotation-view" aria-labelledby="atlas-title">
  <div className="annotation-top"><div><span className="eyebrow">ANNOTATION ATLAS</span><h1 id="atlas-title">How the model learned to explain</h1><p>Training examples from countries covered on the map. The teacher saw the future label; these are separate from the map’s held-out predictions.</p></div><div className="annotation-tabs" role="group" aria-label="Choose training example">{examples.map((e,i)=><button key={e.slug} aria-pressed={i===selected} onClick={()=>switchExample(i)}>{e.slug==='beni'?'Beni · DR Congo':'Oubritenga · Burkina Faso'}</button>)}</div></div>
  <div className="annotation-scroll" ref={panel} key={example.slug}><div className="annotation-content">
   <div className="annotation-case-heading"><div><span className="eyebrow">TRAINING EXAMPLE · {example.transition}</span><h2>{example.slug==='beni'?'Beni':'Oubritenga'}</h2><p>{example.title}</p></div><button onClick={()=>onExplore(country.id)}>Country’s map prediction <ArrowUpRight size={16}/></button></div>
   <div className="annotation-facts"><article><span>Input cutoff</span><strong>{formatDate(example.input.cutoff)}</strong></article><article><span>Known → observed IPC phase</span><strong>{example.input.last_available_phase.phase} → {example.target.phase}</strong></article><article><span>Training target month</span><strong>{example.target.target_month}</strong></article></div>
   <figure className="annotation-figure"><img src={images[example.slug]} alt={`Historical input series and assessment timeline for ${example.slug}`} width="1950" height="1430"/><figcaption>Recorded training inputs. National signals do not establish local exposure; missing observations are not zeros. <a href={images[example.slug]} target="_blank" rel="noreferrer">Open full-size chart ↗</a></figcaption></figure>
   <div className="annotation-section"><span className="eyebrow">01 · OBSERVED SIGNALS</span><h2>What the records contain</h2><div className="annotation-grid">{a.precursor_patterns.map((claim,i)=><article key={i}><span className="annotation-tag">Teacher claim · {claim.provenance}</span><p>{claim.statement}</p><details><summary>Channels and limitations</summary><div className="annotation-channels">{claim.channels.map(c=><code key={c}>{c}</code>)}</div><p>{claim.uncertainty}</p></details></article>)}</div></div>
   <div className="annotation-section"><span className="eyebrow">02 · GENERATED HYPOTHESES</span><h2>Possible connections, with limits</h2><div className="annotation-grid">{a.interaction_hypotheses.map((claim,i)=><article key={i}><p>{claim.statement}</p><details><summary>Proposed mechanism</summary><p>{claim.mechanism}</p><p className="annotation-muted">{claim.uncertainty}</p></details></article>)}</div></div>
   <div className="annotation-section"><span className="eyebrow">03 · TEACHER RATIONALE</span><h2>The explanation used for supervision</h2><blockquote>{a.rationale}</blockquote><p className="annotation-muted">{a.uncertainty}</p></div>
   <details className="annotation-provenance"><summary>Trace this training example</summary><dl><dt>Sample ID</dt><dd>{example.input.sample_id}</dd><dt>Teacher</dt><dd>{example.teacher.model}</dd><dt>Request SHA-256</dt><dd>{example.teacher.request_sha256}</dd></dl><a href={repo+'examples.json'} target="_blank" rel="noreferrer">View exact source records ↗</a></details>
   <p className="annotation-footnote">These selected examples illustrate training supervision, not forecast accuracy or operational guidance.</p>
  </div></div>
 </section>;
}
