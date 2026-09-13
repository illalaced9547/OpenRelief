// Two data paths for the fine-tuned checkpoint's output:
// - liveFor(iso3): a static, batch-generated snapshot (frontend/src/data/live-predictions.json)
//   used for the map, so it renders with no network call and no dependency on the endpoint
//   staying up. Refresh with scripts/generate_live_predictions.py.
// - fetchLive(iso3): a real per-request call to src/open_relief/serve.py, used by the chat
//   panel while the endpoint is kept running. Falls back to the static snapshot, then to
//   an explicit unavailable message if there is no saved output.
import snapshot from '../data/live-predictions.json';

export const ENDPOINT = import.meta.env.VITE_INFERENCE_URL?.trim().replace(/\/+$/, '');
export function liveFor(iso3){
 return iso3 ? snapshot.predictions[iso3] || null : null;
}

const cache = {};

// Share concurrent requests for a country; later requests run inference again.
export function fetchLive(iso3){
 if(!ENDPOINT||!iso3)return Promise.resolve(null);
 if(cache[iso3])return cache[iso3];
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),30000);
 const promise=fetch(`${ENDPOINT}/predict?iso3=${iso3}`,{signal:controller.signal})
  .then(res=>{if(!res.ok)throw new Error(`inference endpoint returned ${res.status}`);return res.json()})
  .then(data=>{if(data?.iso3!==iso3||typeof data.valid_output!=='boolean'||!data.sample_id)throw new Error('Unexpected prediction response');return data})
  .catch(err=>{console.warn('Live model call failed for',iso3,err);delete cache[iso3];return null})
  .finally(()=>{clearTimeout(timeout);delete cache[iso3]});
 cache[iso3]=promise;
 return promise;
}
