// Two data paths for the fine-tuned checkpoint's output:
// - liveFor(iso3): a static, batch-generated snapshot (frontend/src/data/live-predictions.json)
//   used for the map, so it renders with no network call and no dependency on the endpoint
//   staying up. Refresh with scripts/generate_live_predictions.py.
// - fetchLive(iso3): a real per-request call to src/open_relief/serve.py, used by the chat
//   panel while the endpoint is kept running. Falls back to the static snapshot, then to
//   the synthetic demo answers, if the endpoint is unreachable - see ModelChat.jsx.
import snapshot from '../data/live-predictions.json';

export const ENDPOINT = import.meta.env.VITE_INFERENCE_URL?.trim().replace(/\/+$/, '');
export const PHASE_LABEL = {1:'Minimal',2:'Stressed',3:'Crisis',4:'Emergency',5:'Famine'};
export const SNAPSHOT_META = {
 generatedAt: snapshot.generated_at,
 checkpoint: snapshot.checkpoint,
 checkpointSha256: snapshot.checkpoint_sha256,
};

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
  .catch(err=>{console.warn('Live model call failed for',iso3,err);delete cache[iso3];return null})
  .finally(()=>{clearTimeout(timeout);delete cache[iso3]});
 cache[iso3]=promise;
 return promise;
}

// Ordinal IPC phase (1 Minimal - 5 Famine) mapped onto the map's existing 0-100
// risk scale, so the same color/category logic applies to real predictions -
// this is a direct linear mapping of the categorical output, not a calibrated
// probability.
export function riskFromPhase(phase){
 return Math.round((phase-1)/4*100);
}
