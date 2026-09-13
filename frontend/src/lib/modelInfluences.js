// Display exact sentences from the generated rationale, not inferred feature
// importance. Missing price observations and normalization caveats stay limits.
export function modelInfluences(prediction){
 if(!prediction?.valid_output || typeof prediction.rationale!=='string')return [];
 const sentences=prediction.rationale.trim().split(/(?<=[.!?])\s+(?=[A-Z])/).filter(Boolean);
 const rules=[
  {id:'signals',title:'Reported signals',match:/measured precursor|measured numeric patterns|measured signals|precursor signals|observed precursors/i},
  {id:'connection',title:'Possible connection',match:/plausib|hypothes|could|may.*(?:compound|contribut|explain|monitor)|cross-domain mechanism/i},
  {id:'limits',title:'Data limits',match:/unknown normalization|undocumented normalization|directionally uninterpretable|no .*observations.*available/i}
 ];
 const used=new Set();
 return rules.flatMap(rule=>{
  const text=sentences.find(sentence=>rule.match.test(sentence)&&!used.has(sentence));
  if(!text)return [];
  used.add(text);
  return [{id:rule.id,title:rule.title,text}];
 });
}
