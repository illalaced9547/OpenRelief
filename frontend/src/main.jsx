import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowUpRight, ArrowRight, ChevronDown, Globe2, Layers, Plus, Minus, RotateCcw, Search, X, Wheat, Wind, Ship, Info, MoveUpRight, ExternalLink, Crosshair, Activity } from 'lucide-react';
import { geoNaturalEarth1, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import atlas from 'world-atlas/countries-110m.json';
import TrueFocus from './components/TrueFocus';
import GlassSurface from './components/GlassSurface';
import TargetCursor from './components/TargetCursor';
import './index.css';
import './dark.css';
import './neutral.css';
import './insights.css';
import './chat-swap.css';
import ForecastControls from './components/ForecastControls';
import ModelChat from './components/ModelChat';
import CountrySearch from './components/CountrySearch';
import MapBackdrop from './components/MapBackdrop';
import Methodology from './components/Methodology';
import AnnotationAtlas from './components/AnnotationAtlas';
import {clampMapCenter} from './lib/mapBounds';
import {explanationFor} from './data/explanations';
import {liveFor,riskFromPhase,PHASE_LABEL,SNAPSHOT_META} from './lib/liveModel';
import './compact-layout.css';

const countries = feature(atlas, atlas.objects.countries).features.filter(c => c.id !== '010');
// Illustrative scenarios only. Replace this boundary with your colleague's prediction API.
// iso3 marks the 14 countries the fine-tuned checkpoint was evaluated on: chat
// answers for these can come from a live model call (see ModelChat), not just fixtures.
const forecasts = {
 '729': {name:'Sudan',region:'East Africa',risk:87,change:12,point:[30,15],wheat:28},
 '728': {name:'South Sudan',region:'East Africa',risk:82,change:9,point:[30,7],wheat:24},
 '706': {name:'Somalia',region:'East Africa',risk:79,change:8,point:[46,5],wheat:23,iso3:'SOM'},
 '887': {name:'Yemen',region:'Western Asia',risk:84,change:11,point:[48,16],wheat:31},
 '231': {name:'Ethiopia',region:'East Africa',risk:68,change:6,point:[40,9],wheat:18},
 '148': {name:'Chad',region:'Central Africa',risk:72,change:7,point:[19,15],wheat:21},
 '562': {name:'Niger',region:'West Africa',risk:65,change:5,point:[9,17],wheat:17,iso3:'NER'},
 '180': {name:'DR Congo',region:'Central Africa',risk:63,change:6,point:[24,-3],wheat:16,iso3:'COD'},
 '004': {name:'Afghanistan',region:'Southern Asia',risk:71,change:8,point:[66,34],wheat:22},
 '586': {name:'Pakistan',region:'Southern Asia',risk:46,change:4,point:[69,29],wheat:12},
 '818': {name:'Egypt',region:'North Africa',risk:51,change:5,point:[30,27],wheat:19},
 '404': {name:'Kenya',region:'East Africa',risk:43,change:3,point:[38,0],wheat:11,iso3:'KEN'},
 '050': {name:'Bangladesh',region:'Southern Asia',risk:48,change:4,point:[90,24],wheat:13},
 '566': {name:'Nigeria',region:'West Africa',risk:54,change:5,point:[8,9],wheat:14,iso3:'NGA'},
 '076': {name:'Brazil',region:'South America',risk:18,change:1,point:[-52,-10],wheat:4},
 '356': {name:'India',region:'Southern Asia',risk:32,change:2,point:[79,22],wheat:7},
 '710': {name:'South Africa',region:'Southern Africa',risk:26,change:2,point:[25,-29],wheat:6},
 '036': {name:'Australia',region:'Oceania',risk:9,change:1,point:[134,-25],wheat:3},
 '124': {name:'Canada',region:'North America',risk:8,change:1,point:[-106,57],wheat:2},
 '840': {name:'United States',region:'North America',risk:12,change:1,point:[-100,38],wheat:3},
 '250': {name:'France',region:'Europe',risk:10,change:1,point:[2,47],wheat:3},
 '854': {name:'Burkina Faso',region:'West Africa',risk:74,change:7,point:[-1,12],wheat:20,iso3:'BFA'},
 '120': {name:'Cameroon',region:'Central Africa',risk:55,change:4,point:[12,6],wheat:14,iso3:'CMR'},
 '320': {name:'Guatemala',region:'Central America',risk:40,change:3,point:[-90,15],wheat:10,iso3:'GTM'},
 '332': {name:'Haiti',region:'Caribbean',risk:88,change:10,point:[-72,19],wheat:30,iso3:'HTI'},
 '450': {name:'Madagascar',region:'Southern Africa',risk:66,change:6,point:[47,-19],wheat:17,iso3:'MDG'},
 '454': {name:'Malawi',region:'Southern Africa',risk:61,change:5,point:[34,-13],wheat:15,iso3:'MWI'},
 '466': {name:'Mali',region:'West Africa',risk:76,change:8,point:[-4,17],wheat:22,iso3:'MLI'},
 '508': {name:'Mozambique',region:'Southern Africa',risk:58,change:5,point:[35,-18],wheat:14,iso3:'MOZ'},
 '716': {name:'Zimbabwe',region:'Southern Africa',risk:53,change:4,point:[30,-19],wheat:13,iso3:'ZWE'}
};
const category = n => n >= 75 ? 'Critical' : n >= 60 ? 'High' : n >= 35 ? 'Moderate' : 'Low';
const color = n => ({Critical:'#ee8277',High:'#efb775',Moderate:'#e8d985',Low:'#b5d6b7'})[category(n)];
const projection = geoNaturalEarth1().scale(174).translate([520,270]);
const path = geoPath(projection);
function App(){
 const [started,setStarted] = useState(false);
 const [hovered,setHovered] = useState(null);
 const [center,setCenter] = useState([520,270]);
 const [dragging,setDragging] = useState(false);
 const drag = useRef(null);
 const mapRef = useRef(null);
 const [mapTop,setMapTop] = useState(72);
 const [cursorEnabled,setCursorEnabled] = useState(false);
 useEffect(()=>{const media=window.matchMedia('(pointer: fine) and (prefers-reduced-motion: no-preference)');const update=()=>setCursorEnabled(media.matches);update();media.addEventListener('change',update);return()=>media.removeEventListener('change',update)},[]);
 const [selected,setSelected] = useState('729');
 const [horizon,setHorizon] = useState(90);
 const [filter,setFilter] = useState('All risk levels');
 const [query,setQuery] = useState('');
 const [zoom,setZoom] = useState(1);
 const [view,setView] = useState('map');
 useLayoutEffect(()=>{if(!mapRef.current)return;const update=()=>setMapTop(mapRef.current.parentElement.getBoundingClientRect().top);update();window.addEventListener('resize',update);return()=>window.removeEventListener('resize',update)},[started,view]);
 useEffect(()=>{setCenter(c=>clampMapCenter(c,zoom));drag.current=null;setDragging(false)},[zoom]);
 const [detailTab,setDetailTab] = useState('outlook');
 const [chatOpen,setChatOpen] = useState(false);
 useEffect(()=>{if(view!=='map')setChatOpen(false)},[view]);
 useEffect(()=>{
  const map=mapRef.current;
  if(!map)return;
  const wheel=e=>{
   e.preventDefault();e.stopPropagation();setHovered(null);
   const factor=e.deltaMode===1?16:e.deltaMode===2?300:1;
   if(Math.abs(e.deltaX)>Math.abs(e.deltaY)&&!e.ctrlKey){
    const rect=map.getBoundingClientRect();
    const scale=Math.min(rect.width/1040,rect.height/540)*zoom;
    setCenter(c=>clampMapCenter([c[0]+e.deltaX*factor/scale,c[1]],zoom));
    return;
   }
   const delta=e.deltaY*factor;
   setZoom(z=>Math.max(1,Math.min(10,z*Math.exp(-delta*(e.ctrlKey?.012:.002)))));
  };
  const gesture=e=>e.preventDefault();
  map.addEventListener('wheel',wheel,{passive:false});
  map.addEventListener('gesturestart',gesture,{passive:false});
  map.addEventListener('gesturechange',gesture,{passive:false});
  return()=>{map.removeEventListener('wheel',wheel);map.removeEventListener('gesturestart',gesture);map.removeEventListener('gesturechange',gesture)};
 },[started,view,zoom]);


 // Real per-country risk when the live checkpoint has answered for it, else the
 // synthetic fixture (with its demo horizon adjustment, which doesn't apply to a
 // real fixed 3-month forecast).
 const riskFor = d => liveFor(d.iso3) ? riskFromPhase(liveFor(d.iso3).predicted_phase) : Math.max(1,Math.min(99,d.risk + (horizon===30?-8:horizon===180?6:0)));
 const active = forecasts[selected];
 const activeLive = liveFor(active?.iso3);
 const snapshotDate = SNAPSHOT_META.generatedAt?.slice(0,16).replace('T',' ')+' UTC';
 const activeRisk = active ? riskFor(active) : null;
 const explanation = explanationFor(selected,active);
 const selectedName = active?.name || countries.find(c=>c.id===selected)?.properties.name;
 const visible = Object.entries(forecasts).filter(([id,d])=>(filter==='All risk levels'||category(riskFor(d))===filter)&&d.name.toLowerCase().includes(query.trim().toLowerCase()));
 const selectCountry = id => {
  if(drag.current?.moved)return;
  setSelected(id);setQuery('');setHovered(null);

 };
 const showHover=(e,c)=>{if(drag.current)return;const d=forecasts[c.id];setHovered({name:c.properties.name,risk:d?riskFor(d):null,live:!!liveFor(d?.iso3),phase:liveFor(d?.iso3)?.predicted_phase,x:Math.min(e.clientX+20,window.innerWidth-170),y:Math.min(e.clientY+20,window.innerHeight-80)})};
 const resetMap=()=>{setZoom(1);setCenter([520,270]);setFilter('All risk levels');setQuery('');setHovered(null)};
 if(!started)return <div className="landing">
  <header><a href="#" onClick={()=>setStarted(false)} className="brand"><svg className="relief-logo" width="34" height="34" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M30.5 8.5A15.5 15.5 0 1 0 35 24" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity=".65"/><path d="M19.5 31V13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M19.5 14C16 11 17 7.5 19.5 5.5C22 7.5 23 11 19.5 14ZM19.5 20C14 20 11 16.5 11.5 12.5C16 12.5 19.5 15.5 19.5 20ZM19.5 26C14 26 10.5 23 11 19C15.5 19 19.5 22 19.5 26ZM19.5 20C25 20 28 16.5 27.5 12.5C23 12.5 19.5 15.5 19.5 20ZM19.5 26C25 26 28.5 23 28 19C23.5 19 19.5 22 19.5 26Z" fill="currentColor"/><circle cx="34" cy="15" r="2.5" fill="currentColor"/><circle cx="34" cy="15" r="5" stroke="currentColor" strokeWidth=".8" opacity=".3"/></svg> OpenRelief<span className="brand-dot">®</span></a><span className="prototype"><i/> Research preview</span></header>
  <MapBackdrop countries={countries} forecasts={forecasts} color={color}/>
  <main className="landing-content"><div className="eyebrow"><span/> EARLY INSIGHT. EARLIER ACTION.</div><h1 className="hero-title" aria-label="OpenRelief"><TrueFocus sentence="Open Relief" blurAmount={3} borderColor="#cccccc" glowColor="transparent" animationDuration={0.6} pauseBetweenAnimations={2.5}/></h1><p className="landing-tagline">Predict hunger.</p><p className="hackathon">EHL Hackathon 2026 <span>—</span> Zurich</p><GlassSurface width={190} height={56} borderRadius={28} backgroundOpacity={0.08} distortionScale={-35} className="start-glass"><button className="get-started" onClick={()=>setStarted(true)}>Get started <ArrowRight size={17}/></button></GlassSurface></main>
  <div className="landing-footer"><span>INTELLIGENCE FOR HUMANITY</span><span>47.3769° N &nbsp; 8.5417° E</span></div>
 </div>;

 return <div className="app-shell dark-dashboard">
  {view!=='map'&&<MapBackdrop countries={countries} forecasts={forecasts} color={color}/>}
  {cursorEnabled&&view==='map'&&!dragging&&<TargetCursor key={`${zoom}-${center.join()}-${view}`} targetSelector=".country" scopeSelector=".world-map" hideDefaultCursor={false} spinDuration={5} parallaxOn={false} cursorColor="#cccccc"/>}
  {hovered&&<div className="country-tooltip" style={{left:hovered.x,top:hovered.y}}><span>{hovered.name}</span><strong style={{color:hovered.risk!==null?color(hovered.risk):'#aaa'}}>{hovered.live?`IPC ${hovered.phase ?? '?'}/5`:hovered.risk!==null?`${hovered.risk}%`:'No data'}</strong><small>{hovered.live?'HISTORICAL MODEL SAMPLE':'DEMO RISK'}</small></div>}
  <header><a href="#" onClick={()=>setStarted(false)} className="brand"><svg className="relief-logo" width="34" height="34" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M30.5 8.5A15.5 15.5 0 1 0 35 24" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity=".65"/><path d="M19.5 31V13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M19.5 14C16 11 17 7.5 19.5 5.5C22 7.5 23 11 19.5 14ZM19.5 20C14 20 11 16.5 11.5 12.5C16 12.5 19.5 15.5 19.5 20ZM19.5 26C14 26 10.5 23 11 19C15.5 19 19.5 22 19.5 26ZM19.5 20C25 20 28 16.5 27.5 12.5C23 12.5 19.5 15.5 19.5 20ZM19.5 26C25 26 28.5 23 28 19C23.5 19 19.5 22 19.5 26Z" fill="currentColor"/><circle cx="34" cy="15" r="2.5" fill="currentColor"/><circle cx="34" cy="15" r="5" stroke="currentColor" strokeWidth=".8" opacity=".3"/></svg> OpenRelief<span className="brand-dot">®</span></a><nav><button className={view==='map'?'nav-active':''} onClick={()=>setView('map')}>Risk overview</button><button className={view==='signals'?'nav-active':''} onClick={()=>setView('signals')}>Global insights</button><button className={view==='methodology'?'nav-active':''} onClick={()=>setView('methodology')}>Our methodology <ArrowUpRight size={13}/></button><button className={view==='annotation-atlas'?'nav-active':''} onClick={()=>setView('annotation-atlas')}>Annotation atlas</button><button className={view==='roadmap'?'nav-active':''} onClick={()=>setView('roadmap')}>Roadmap</button></nav><span className="prototype"><i/> Research preview</span></header>
  <main>  <section className="workspace">
  {view==='map'?<div className="map-stage">
  <div className="map-body"><div className="map-area"><div className="map-top"><CountrySearch countries={visible} query={query} setQuery={setQuery} onSelect={selectCountry} selected={selected} riskFor={riskFor} color={color}/><ForecastControls horizon={horizon} setHorizon={setHorizon} filter={filter} setFilter={setFilter}/></div>
  <svg className={`world-map ${dragging?'is-dragging':''}`} ref={mapRef} style={{'--map-offset-top':`${mapTop}px`}} onPointerDown={e=>{if(e.button!==0)return;drag.current={x:e.clientX,y:e.clientY,center:[...center],moved:false};setDragging(true)}} onPointerMove={e=>{if(!drag.current)return;const dx=e.clientX-drag.current.x,dy=e.clientY-drag.current.y;if(Math.abs(dx)+Math.abs(dy)>5){drag.current.moved=true;e.currentTarget.setPointerCapture(e.pointerId);setHovered(null);const rect=e.currentTarget.getBoundingClientRect();const scale=Math.min(rect.width/1040,rect.height/540)*zoom;setCenter(clampMapCenter([drag.current.center[0]-dx/scale,drag.current.center[1]-dy/scale],zoom))}}} onPointerUp={()=>{setDragging(false);setTimeout(()=>{drag.current=null},0)}} onPointerCancel={()=>{drag.current=null;setDragging(false)}} onPointerLeave={()=>{setHovered(null);if(!drag.current?.moved){drag.current=null;setDragging(false)}}} viewBox="0 0 1040 540" role="group" aria-label="Interactive world map of illustrative food insecurity risk"><defs><pattern id="dots" width="13" height="13" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.65" fill="#888888" opacity=".18"/></pattern></defs><rect width="1040" height="540" fill="url(#dots)"/><g className="map-geography" style={{transition:'none'}} transform={`translate(${520-center[0]*zoom},${270-center[1]*zoom}) scale(${zoom})`}>{[-1,0,1].map(copy=><g key={copy} transform={`translate(${copy*1040},0)`}>{countries.map(c=>{const d=forecasts[c.id];const matches=d&&(filter==='All risk levels'||category(riskFor(d))===filter)&&(!query||d.name.toLowerCase().includes(query.trim().toLowerCase()));return <path key={c.id} d={path(c)} fill={matches?color(riskFor(d)):'#777777'} fillOpacity={matches?.72:.33} stroke={selected===c.id?'#cccccc':'#999999'} strokeOpacity={selected===c.id?.8:.26} strokeWidth={selected===c.id?1.4:.6} vectorEffect="non-scaling-stroke" className="country" role="button" tabIndex={copy===0?0:-1} onPointerEnter={e=>showHover(e,c)} onPointerMove={e=>showHover(e,c)} onPointerLeave={()=>setHovered(null)} aria-label={`${c.properties.name}: ${d?riskFor(d)+' percent illustrative risk':'no demo data'}`} onClick={()=>selectCountry(c.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectCountry(c.id)}}}/>})}</g>)}</g></svg>
  <div className="map-bottom"><div className="legend"><span>RISK LEVEL</span>{[['Low','#b5d6b7'],['Moderate','#e8d985'],['High','#efb775'],['Critical','#ee8277'],['No data','#dce0d7']].map(([name,c])=><button key={name} onClick={()=>name!=='No data'&&setFilter(filter===name?'All risk levels':name)} className={filter===name?'legend-active':''}><i style={{background:c}}/>{name}</button>)}</div><div className="zoom-controls"><button aria-label="Zoom in" onClick={()=>setZoom(Math.min(zoom*1.5,10))}><Plus size={15}/></button><button aria-label="Zoom out" onClick={()=>setZoom(Math.max(zoom/1.5,1))}><Minus size={15}/></button><button aria-label="Reset map" onClick={resetMap}><RotateCcw size={13}/></button></div></div></div>
  <aside className={`country-panel explanation-panel ${chatOpen?'panel-away':''}`} inert={chatOpen} aria-hidden={chatOpen}><div className="panel-eyebrow">COUNTRY INTELLIGENCE <span className="demo-pill" style={activeLive?{color:'#b5d6b7',borderColor:'#b5d6b7'}:undefined}>{activeLive?'MODEL FORECAST':'DEMO'}</span></div><div className="country-heading"><h3>{selectedName}</h3><Crosshair size={20}/></div><p className="region">{active?.region||'Outside demo coverage'}</p>{active?<><div className="detail-tabs" role="group" aria-label="Country detail view">{[['outlook','Outlook'],['explanation','Explanation'],['sources','Sources']].map(([id,label])=><button key={id} aria-pressed={detailTab===id} onClick={()=>setDetailTab(id)}>{label}</button>)}</div><div className="detail-content">
  {detailTab==='outlook'?<>{activeLive?<><div className="probability"><span>{activeLive.predicted_phase||'?'}<small>/5</small></span><span className="risk-badge" style={{color:color(activeRisk),background:color(activeRisk)+'26'}}>{activeLive.predicted_phase?PHASE_LABEL[activeLive.predicted_phase]:'Unparsed output'}</span></div><p className="probability-label">Fine-tuned checkpoint's predicted FEWS NET IPC phase<br/>for {activeLive.target_month} (cutoff {activeLive.cutoff?.slice(0,10)})</p><div className="confidence-card"><div><span>Held-out test sample</span><strong style={{fontSize:13}}>{activeLive.sample_id}</strong></div><p>Generated by best_model.pt as a batch snapshot ({snapshotDate}) · {activeLive.num_examples_for_country} test examples available for {activeLive.country}</p></div><button className="explanation-preview" onClick={()=>setDetailTab('explanation')}><span>What's the model's rationale?</span><strong>{activeLive.valid_output?'Read the generated explanation':'Output did not parse as valid JSON'}</strong><ArrowRight size={16}/></button></>:<><div className="probability"><span>{activeRisk}<small>%</small></span><span className="risk-badge" style={{color:color(activeRisk),background:color(activeRisk)+'26'}}>{category(activeRisk)} risk</span></div><p className="probability-label">Risk of increased food insecurity<br/>in the next {horizon} days</p><div className="confidence-card"><div><span>Prediction confidence</span><strong>{explanation.confidence}<small>%</small></strong></div><div className="confidence-bar"><i style={{width:explanation.confidence+'%'}}/></div><p>Illustrative score · Not calibrated accuracy</p></div><div className="price-card"><span className="section-kicker">PRICE OBSERVATION</span><div><strong>${explanation.price.current}<small> / tonne</small></strong><span>+{explanation.price.changePct}% <ArrowUpRight size={13}/></span></div><p>{explanation.price.commodity}</p><small>From ${explanation.price.previous} · {explanation.price.period}</small></div><button className="explanation-preview" onClick={()=>setDetailTab('explanation')}><span>What could explain this?</span><strong>{explanation.title}</strong><ArrowRight size={16}/></button></>}</>:detailTab==='explanation'?<>{activeLive?<><span className="section-kicker">MODEL RATIONALE</span><h4>Predicted phase {activeLive.predicted_phase} — {activeLive.predicted_phase?PHASE_LABEL[activeLive.predicted_phase]:'unparsed'}</h4><p>{activeLive.valid_output?activeLive.rationale:activeLive.raw_output}</p>{activeLive.recommended_actions?.length>0&&<><span className="section-kicker">RECOMMENDED FOLLOW-UP</span><p>{activeLive.recommended_actions.join('; ')}</p></>}<div className="uncertainty-note"><Info size={15}/><p>Generated by the fine-tuned checkpoint from real time-series evidence only; this is a categorical phase prediction and rationale, not a calibrated probability.</p></div></>:<><span className="section-kicker">POSSIBLE EXPLANATION</span><h4>{explanation.title}</h4><p>{explanation.hypothesis}</p><span className="section-kicker">HOW THE PREDICTION IS FORMED</span><p>{explanation.method}</p><div className="uncertainty-note"><Info size={15}/><p>{explanation.limitation}</p></div><p className="hypothesis-note">A hypothesis is not proof of causation. This scenario is fictional.</p></>}</>:<>{activeLive?<><span className="section-kicker">EVIDENCE & PROVENANCE</span><div className="source-row"><span>Held-out test sample</span><small>{activeLive.sample_id}</small></div><div className="source-row"><span>Forecast cutoff</span><small>{activeLive.cutoff}</small></div><div className="source-row"><span>Target month</span><small>{activeLive.target_month}</small></div><div className="source-metadata"><span>Model <strong>OpenTSLM-SP + LoRA, all-sources checkpoint</strong></span><span>Snapshot <strong>{snapshotDate}</strong></span></div><p className="hypothesis-note">This is the fine-tuned checkpoint's real output on a stored held-out test example, generated as a batch snapshot — not recomputed on each visit, and not a forecast for an arbitrary date.</p></>:<><span className="section-kicker">EVIDENCE & PROVENANCE</span><p>The model will return the records supporting each explanation, including their origin and observation date.</p>{explanation.sources.map(source=><div className="source-row" key={source.id}><span>{source.name}</span><small>{source.status}</small></div>)}<div className="source-metadata"><span>Model version <strong>Awaiting integration</strong></span><span>Data timestamp <strong>Not available</strong></span></div><p className="hypothesis-note">No sources were retrieved for this demo. Source categories are illustrative, not fixed inputs.</p></>}</>}
  </div></>:<div className="empty-state"><Globe2 size={28}/><p>No prediction, explanation or confidence score is available for this country in the demo.</p><button onClick={()=>selectCountry('729')}>Explore Sudan <ArrowRight size={14}/></button></div>}</aside></div>
  <div className="map-footer"><span><Info size={12}/> Scroll to zoom · Drag or swipe sideways to explore the world</span><span>14 countries show the fine-tuned checkpoint's batch-generated forecast ({snapshotDate}); the rest remain illustrative</span></div></div>:view==='roadmap'?<section className="roadmap"><div className="roadmap-intro"><span className="eyebrow">WHAT COMES NEXT</span><h1>From signals to action.</h1><p>A proposed path for OpenRelief, from this research preview to a useful early-warning system.</p></div><div className="roadmap-grid">{[
 ['01','Now','Explore the outlook','Build the interactive map and make country-level demo scenarios easy to understand.'],
 ['02','Next','Connect the model','Integrate the prediction service and replace synthetic scenarios with model outputs.'],
 ['03','Planned','Validate the signals','Evaluate predictions against historical outcomes, document sources, and communicate uncertainty.'],
 ['04','Future','Support earlier action','Explore alerts, regional monitoring, and workflows with relief organizations.']
 ].map(([n,status,title,description])=><article key={n}><div className="roadmap-step"><span>{n}</span><span className="demo-pill">{status}</span></div><h2>{title}</h2><p>{description}</p></article>)}</div><p className="roadmap-note">Proposed milestones · No release dates committed</p></section>:view==='methodology'?<Methodology onExplore={id=>{setSelected(id);setHorizon(90);setDetailTab('outlook');setView('map')}}/>:view==='annotation-atlas'?<AnnotationAtlas/>:<section className="model-insights"><div className="insight-intro"><span className="eyebrow">GLOBAL INSIGHTS</span><h1>The story behind the signals.</h1><p>Price movements are the starting point. The model will connect them to possible explanations and show the evidence behind each one.</p><span className="demo-pill">MODEL FEED NOT CONNECTED</span></div><div className="insight-grid">{[['729','Price pressure'],['706','Possible disruption'],['566','Alternative explanations']].map(([id,label])=>{const country=forecasts[id],detail=explanationFor(id,country);return <article key={id}><div className="insight-card-top"><span>{label}</span><span>DEMO</span></div><h2>{detail.title}</h2><p>{detail.hypothesis}</p><div className="insight-price"><span>{country.name} · Wheat</span><strong>+{country.wheat}%</strong></div><button onClick={()=>{setSelected(id);setDetailTab('explanation');setView('map')}}>Explore explanation <ArrowUpRight size={16}/></button></article>})}</div><div className="provenance-banner"><div><Layers size={22}/><h3>Every insight should have a source.</h3></div><p>The future trained-model feed should include source records and links, observation dates, model version, confidence and alternative explanations. Inputs can vary by event and country; they are not limited to three signal types.</p><span>Sources, timestamps and model outputs are pending integration.</span></div></section>}

  </section></main>
  <ModelChat open={chatOpen&&view==='map'} onOpen={()=>{setView('map');setChatOpen(true)}} onClose={()=>setChatOpen(false)} context={{country:selectedName,horizon,risk:activeRisk,explanation,iso3:active?.iso3}}/>

 </div>
}
createRoot(document.getElementById('root')).render(<App/>);
