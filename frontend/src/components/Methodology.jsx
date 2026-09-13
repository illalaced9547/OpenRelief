import {ArrowUpRight,TrendingUp,Ship,Landmark,CloudSun,Layers,BrainCircuit,ScanLine,ShieldCheck,ArrowDown} from 'lucide-react';
import './Methodology.css';
import {modelCountries,PHASE_LABEL,phaseColor} from '../data/modelData';
const inputs=[
 {Icon:Layers,title:'Food-security history',subtitle:'HFID FCS/rCSI · Prior IPC phase'},
 {Icon:Ship,title:'Shipping activity',subtitle:'PortWatch · Cargo & port calls'},
 {Icon:Landmark,title:'Conflict indicators',subtitle:'ACLED · Events & fatalities'},
 {Icon:CloudSun,title:'Rainfall history',subtitle:'CHIRPS · Monthly rainfall'},
 {Icon:TrendingUp,title:'Staple-food prices',subtitle:'WFP · Prices & trailing changes'}
];
export default function Methodology({onExplore}){
 return <section className="method-page"><div className="method-intro"><span className="eyebrow">OUR METHODOLOGY</span><h1>Six months of signals. A three-month outlook.</h1></div><div className="method-column-labels"><span>01 &nbsp; OBSERVE THE WORLD</span><span>02 &nbsp; PROCESS THE HISTORY</span><span>03 &nbsp; PREDICT IPC PHASE</span></div><div className="method-flow">
 <svg className="flow-wires" viewBox="0 0 1000 480" preserveAspectRatio="none" aria-hidden="true">{[42,141,240,339,438].map((y,i)=><path key={y} d={`M240 ${y} C330 ${y},330 240,410 240`}/>)}{[95,240,385].map(y=><path key={y} d={`M590 240 C675 240,675 ${y},760 ${y}`}/>)}{[42,141,240,339,438].map(y=><circle key={`in-${y}`} className="wire-pulse" r="3"><animateMotion begin="0s" dur="4s" repeatCount="indefinite" calcMode="linear" keyPoints="0;1;1" keyTimes="0;0.5;1" path={`M240 ${y} C330 ${y},330 240,410 240`}/><animate attributeName="opacity" begin="0s" dur="4s" repeatCount="indefinite" calcMode="discrete" values="1;0;0" keyTimes="0;0.5;1"/></circle>)}{[95,240,385].map(y=><circle key={`out-${y}`} className="wire-pulse" r="3" opacity="0"><animateMotion begin="0s" dur="4s" repeatCount="indefinite" calcMode="linear" keyPoints="0;0;1" keyTimes="0;0.5;1" path={`M590 240 C675 240,675 ${y},760 ${y}`}/><animate attributeName="opacity" begin="0s" dur="4s" repeatCount="indefinite" calcMode="discrete" values="0;1;1" keyTimes="0;0.5;1"/></circle>)}</svg>
 <div className="input-stack">{inputs.map(({Icon,title,subtitle})=><div key={title} className="signal-node"><Icon size={20}/><span><strong>{title}</strong><small>{subtitle}</small></span><span className="node-port"/></div>)}</div>
 <ArrowDown className="mobile-flow-arrow" aria-hidden="true"/>
 <div className="model-column"><div className="model-node"><div className="model-orbit"><BrainCircuit size={36} strokeWidth={1.2}/></div><span className="section-kicker">OpenTSLM-SP + LoRA</span><h2>Predict three months ahead.</h2><div className="model-steps"><span><ScanLine size={14}/> 21 monthly input channels</span><span><Layers size={14}/> Generate phase & rationale</span><span><ShieldCheck size={14}/> Six-month history window</span></div><span className="model-status"><i/> Checkpoint connected</span></div></div>
 <ArrowDown className="mobile-flow-arrow" aria-hidden="true"/>
 <div className="output-stack">{['332','454','404'].map(id=>{const d=modelCountries[id],tint=phaseColor(d.phase);return <button className="prediction-node" key={id} onClick={()=>onExplore(id)}><div><span><i style={{background:tint}}/>{d.name}</span><ArrowUpRight size={16}/></div><strong style={{color:tint}}>{d.phase}<small>/5</small></strong><p>{PHASE_LABEL[d.phase]}</p><footer><span>Target {d.target_month}</span><span>EXPLORE</span></footer></button>})}</div>
 </div><div className="method-notes"><span>CONNECTED MODEL · HISTORICAL SAMPLES</span><span>One district sample per country · Rationales are generated hypotheses</span></div></section>;
}
