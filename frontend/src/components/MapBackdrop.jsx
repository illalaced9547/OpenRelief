import {memo} from 'react';
import {geoNaturalEarth1,geoPath} from 'd3-geo';
import './MapBackdrop.css';
const projection=geoNaturalEarth1().scale(174).translate([520,270]);
const draw=geoPath(projection);
export default memo(function MapBackdrop({countries,forecasts,color}){
 return <div className="decorative-map" aria-hidden="true"><svg viewBox="0 0 1040 540">{countries.map(c=>{const data=forecasts[c.id];return <path key={c.id} d={draw(c)} fill={data?color(data.risk):'#8f9696'} fillOpacity={data?.72:.5} stroke="#161a1b" strokeWidth=".8"/>})}</svg><div className="decorative-map-shade"/></div>;
});
