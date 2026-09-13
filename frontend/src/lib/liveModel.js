// Static checkpoint-generated predictions for the model's 14 evaluated countries.
// Batch-generated once from src/open_relief/serve.py (one held-out test example per
// country) and committed as a snapshot - not fetched live per page view or per
// keystroke. Intended production cadence: re-run the batch daily/weekly against a
// live cutoff and replace this file; see scripts/generate_live_predictions.py.
import snapshot from '../data/live-predictions.json';

export const PHASE_LABEL = {1:'Minimal',2:'Stressed',3:'Crisis',4:'Emergency',5:'Famine'};
export const SNAPSHOT_META = {
 generatedAt: snapshot.generated_at,
 checkpoint: snapshot.checkpoint,
 checkpointSha256: snapshot.checkpoint_sha256,
};

// Synchronous lookup - no network call, no loading state needed.
export function liveFor(iso3){
 return iso3 ? snapshot.predictions[iso3] || null : null;
}

// Ordinal IPC phase (1 Minimal - 5 Famine) mapped onto the map's existing 0-100
// risk scale, so the same color/category logic applies to real predictions -
// this is a direct linear mapping of the categorical output, not a calibrated
// probability.
export function riskFromPhase(phase){
 return Math.round((phase-1)/4*100);
}
