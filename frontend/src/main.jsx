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
import CountryDetails from './components/CountryDetails';
import {GlobalInsights,Roadmap} from './components/ModelPages';
import {modelCountries,phaseColor,PHASE_LABEL,snapshotMeta,formatDate} from './data/modelData';
import './model-pages.css';

import './compact-layout.css';

const countries = feature(atlas, atlas.objects.countries).features.filter(c => c.id !== '010');
const forecasts = modelCountries;
const category = n => PHASE_LABEL[n] || 'No model data';
const color = phaseColor;
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
 const [selected,setSelected] = useState('566');
 const [filter,setFilter] = useState('All IPC phases');
 const [query,setQuery] = useState('');
 const [zoom,setZoom] = useState(1);
 const [view,setView] = useState('map');
 useLayoutEffect(()=>{if(!mapRef.current)return;const update=()=>setMapTop(mapRef.current.parentElement.getBoundingClientRect().top);update();window.addEventListener('resize',update);return()=>window.removeEventListener('resize',update)},[started,view]);
 useEffect(()=>{setCenter(c=>clampMapCenter(c,zoom));drag.current=null;setDragging(false)},[zoom]);
 const [detailTab,setDetailTab] = useState('outlook');
 const [mobileDetailOpen,setMobileDetailOpen] = useState(false);
 const [chatOpen,setChatOpen] = useState(false);
 useEffect(()=>{if(view!=='map'){setChatOpen(false);setMobileDetailOpen(false)}},[view]);
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


 const riskFor = d => d.phase;
 const active = forecasts[selected];
 const snapshotDate = formatDate(snapshotMeta.generatedAt);
 const selectedName = active?.name || countries.find(c=>c.id===selected)?.properties.name;
 const visible = Object.entries(forecasts).filter(([id,d])=>(filter==='All IPC phases'||category(riskFor(d))===filter)&&d.name.toLowerCase().includes(query.trim().toLowerCase()));
 const selectCountry = id => {
  if(drag.current?.moved)return;
  setSelected(id);setQuery('');setHovered(null);
  setMobileDetailOpen(true);

 };
 const showHover=(e,c)=>{if(drag.current)return;const d=forecasts[c.id];setHovered({name:c.properties.name,phase:d?.phase ?? null,x:Math.min(e.clientX+20,window.innerWidth-210),y:Math.min(e.clientY+20,window.innerHeight-100)})};
 const resetMap=()=>{setZoom(1);setCenter([520,270]);setFilter('All IPC phases');setQuery('');setHovered(null)};
 if(!started)return <div className="landing">
  <header><a href="#" onClick={()=>setStarted(false)} className="brand"><svg className="relief-logo" width="34" height="34" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M30.5 8.5A15.5 15.5 0 1 0 35 24" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity=".65"/><path d="M19.5 31V13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M19.5 14C16 11 17 7.5 19.5 5.5C22 7.5 23 11 19.5 14ZM19.5 20C14 20 11 16.5 11.5 12.5C16 12.5 19.5 15.5 19.5 20ZM19.5 26C14 26 10.5 23 11 19C15.5 19 19.5 22 19.5 26ZM19.5 20C25 20 28 16.5 27.5 12.5C23 12.5 19.5 15.5 19.5 20ZM19.5 26C25 26 28.5 23 28 19C23.5 19 19.5 22 19.5 26Z" fill="currentColor"/><circle cx="34" cy="15" r="2.5" fill="currentColor"/><circle cx="34" cy="15" r="5" stroke="currentColor" strokeWidth=".8" opacity=".3"/></svg> OpenRelief<span className="brand-dot">®</span></a><span className="prototype"><i/> Research preview</span></header>
  <MapBackdrop countries={countries} forecasts={forecasts} color={color}/>
  <main className="landing-content"><div className="eyebrow"><span/> EARLY INSIGHT · EARLIER ACTION</div><h1 className="hero-title" aria-label="OpenRelief"><TrueFocus sentence="Open Relief" blurAmount={3} borderColor="#cccccc" glowColor="transparent" animationDuration={0.6} pauseBetweenAnimations={2.5}/></h1><p className="landing-tagline">Predict the food crisis</p><p className="hackathon">EHL Hackathon 2026 <span>—</span> Zurich</p><GlassSurface width={190} height={56} borderRadius={28} backgroundOpacity={0.08} distortionScale={-35} className="start-glass"><button className="get-started" onClick={()=>setStarted(true)}>Get started <ArrowRight size={17}/></button></GlassSurface></main>
  <div className="landing-footer"><span>INTELLIGENCE FOR HUMANITY</span><span>47.3769° N &nbsp; 8.5417° E</span></div>
 </div>;

 return <div className="app-shell dark-dashboard">
  {view!=='map'&&<MapBackdrop countries={countries} forecasts={forecasts} color={color}/>}
  {cursorEnabled&&view==='map'&&!dragging&&<TargetCursor key={`${zoom}-${center.join()}-${view}`} targetSelector=".country" scopeSelector=".world-map" hideDefaultCursor={false} spinDuration={5} parallaxOn={false} cursorColor="#cccccc"/>}
  {hovered&&<div className="country-tooltip" style={{left:hovered.x,top:hovered.y}}><span>{hovered.name}</span><strong style={{color:color(hovered.phase)}}>{hovered.phase?`IPC ${hovered.phase}/5`:'No model data'}</strong><small>{hovered.phase?`${category(hovered.phase)} · Historical sample`:'No forecast supplied'}</small></div>}

  <header><a href="#" onClick={()=>setStarted(false)} className="brand"><svg className="relief-logo" width="34" height="34" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M30.5 8.5A15.5 15.5 0 1 0 35 24" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity=".65"/><path d="M19.5 31V13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M19.5 14C16 11 17 7.5 19.5 5.5C22 7.5 23 11 19.5 14ZM19.5 20C14 20 11 16.5 11.5 12.5C16 12.5 19.5 15.5 19.5 20ZM19.5 26C14 26 10.5 23 11 19C15.5 19 19.5 22 19.5 26ZM19.5 20C25 20 28 16.5 27.5 12.5C23 12.5 19.5 15.5 19.5 20ZM19.5 26C25 26 28.5 23 28 19C23.5 19 19.5 22 19.5 26Z" fill="currentColor"/><circle cx="34" cy="15" r="2.5" fill="currentColor"/><circle cx="34" cy="15" r="5" stroke="currentColor" strokeWidth=".8" opacity=".3"/></svg> OpenRelief<span className="brand-dot">®</span></a><nav><button className={view==='map'?'nav-active':''} onClick={()=>setView('map')}>Risk overview</button><button className={view==='signals'?'nav-active':''} onClick={()=>setView('signals')}>Global insights</button><button className={view==='methodology'?'nav-active':''} onClick={()=>setView('methodology')}>Our methodology <ArrowUpRight size={13}/></button><button className={view==='annotation-atlas'?'nav-active':''} onClick={()=>setView('annotation-atlas')}>Annotation atlas</button><button className={view==='roadmap'?'nav-active':''} onClick={()=>setView('roadmap')}>Roadmap</button></nav><span className="prototype"><i/> Research preview</span></header>
  <main className={view==='map'?'map-main':''}>  <section className="workspace">
  {view==='map'?<div className="map-stage">
  <div className="map-body"><div className="map-area"><div className="map-top"><CountrySearch countries={visible} query={query} setQuery={setQuery} onSelect={selectCountry} selected={selected} riskFor={riskFor} color={color}/><ForecastControls filter={filter} setFilter={setFilter}/></div>
  <svg className={`world-map ${dragging?'is-dragging':''}`} ref={mapRef} style={{'--map-offset-top':`${mapTop}px`}} onPointerDown={e=>{if(e.button!==0)return;drag.current={x:e.clientX,y:e.clientY,center:[...center],moved:false};setDragging(true)}} onPointerMove={e=>{if(!drag.current)return;const dx=e.clientX-drag.current.x,dy=e.clientY-drag.current.y;if(Math.abs(dx)+Math.abs(dy)>5){drag.current.moved=true;e.currentTarget.setPointerCapture(e.pointerId);setHovered(null);const rect=e.currentTarget.getBoundingClientRect();const scale=Math.min(rect.width/1040,rect.height/540)*zoom;setCenter(clampMapCenter([drag.current.center[0]-dx/scale,drag.current.center[1]-dy/scale],zoom))}}} onPointerUp={()=>{setDragging(false);setTimeout(()=>{drag.current=null},0)}} onPointerCancel={()=>{drag.current=null;setDragging(false)}} onPointerLeave={()=>{setHovered(null);if(!drag.current?.moved){drag.current=null;setDragging(false)}}} viewBox="0 0 1040 540" role="group" aria-label="Historical model predictions by country; one district sample per country"><defs><pattern id="dots" width="13" height="13" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.65" fill="#888888" opacity=".18"/></pattern></defs><rect width="1040" height="540" fill="url(#dots)"/><g className="map-geography" style={{transition:'none'}} transform={`translate(${520-center[0]*zoom},${270-center[1]*zoom}) scale(${zoom})`}>{[-1,0,1].map(copy=><g key={copy} transform={`translate(${copy*1040},0)`}>{countries.map(c=>{const d=forecasts[c.id];const matches=d&&(filter==='All IPC phases'||category(riskFor(d))===filter)&&(!query||d.name.toLowerCase().includes(query.trim().toLowerCase()));return <path key={c.id} d={path(c)} fill={matches?color(riskFor(d)):'#777777'} fillOpacity={matches?.72:.33} stroke={selected===c.id?'#cccccc':'#999999'} strokeOpacity={selected===c.id?.8:.26} strokeWidth={selected===c.id?1.4:.6} vectorEffect="non-scaling-stroke" className="country" role="button" tabIndex={copy===0?0:-1} onPointerEnter={e=>showHover(e,c)} onPointerMove={e=>showHover(e,c)} onPointerLeave={()=>setHovered(null)} aria-label={`${c.properties.name}: ${d?.phase?'Predicted IPC phase '+d.phase+', historical district sample':'no model data'}`} onClick={()=>selectCountry(c.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectCountry(c.id)}}}/>})}</g>)}</g></svg>
  <div className="map-bottom"><div className="legend"><span>IPC PHASE</span>{Object.entries(PHASE_LABEL).map(([phase,label])=><button key={phase} onClick={()=>setFilter(filter===label?'All IPC phases':label)} className={filter===label?'legend-active':''}><i style={{background:color(Number(phase))}}/>{phase} {label}</button>)}<span className="legend-no-data"><i style={{background:'#777'}}/>No model data</span></div><div className="zoom-controls"><button aria-label="Zoom in" onClick={()=>setZoom(Math.min(zoom*1.5,10))}><Plus size={15}/></button><button aria-label="Zoom out" onClick={()=>setZoom(Math.max(zoom/1.5,1))}><Minus size={15}/></button><button aria-label="Reset map" onClick={resetMap}><RotateCcw size={13}/></button></div></div></div>
  <CountryDetails country={active} name={selectedName} tab={detailTab} setTab={setDetailTab} mobileOpen={mobileDetailOpen} onClose={()=>setMobileDetailOpen(false)} hidden={chatOpen}/></div>
  <div className="map-footer"><span><Info size={12}/> Scroll to zoom · Drag sideways to explore</span><span>{Object.keys(forecasts).length} historical district samples · Snapshot {snapshotDate} · Country shading is not a national forecast</span></div></div>:view==='roadmap'?<Roadmap/>:view==='methodology'?<Methodology onExplore={id=>{setSelected(id);setDetailTab('outlook');setView('map')}}/>:view==='annotation-atlas'?<AnnotationAtlas onExplore={id=>{setSelected(id);setDetailTab('sources');setView('map')}}/>:<GlobalInsights onExplore={id=>{setSelected(id);setDetailTab('explanation');setView('map')}}/>}


  </section></main>
  <ModelChat open={chatOpen&&view==='map'} onOpen={()=>{setView('map');setChatOpen(true)}} onClose={()=>setChatOpen(false)} context={{country:selectedName,iso3:active?.iso3}} hidden={view!=='map'}/>

 </div>
}
createRoot(document.getElementById('root')).render(<App/>);
