// Synthetic frontend fixtures. These are hypotheses, not real events or model output.
const scenarios = [
 {title:'Import costs may be passing through to local prices', hypothesis:'In this scenario, higher landed costs and limited alternative suppliers could make staple foods less affordable. Currency weakness or procurement constraints could amplify the price move.', evidence:['Local staple-price series','Import dependence and exchange rates'], confidence:68, limitation:'Supplier-level coverage and household purchasing power are missing.'},
 {title:'A trade-route disruption could tighten supply', hypothesis:'A hypothetical chokepoint disruption, such as restricted passage through the Strait of Hormuz, could raise fuel, freight or insurance costs. Exposure would depend on the routes and suppliers actually used; no such event is asserted here.', evidence:['Route exposure and freight quotes','Supplier and inventory records'], confidence:56, limitation:'Route exposure must be verified before linking a disruption to this country.'},
 {title:'Domestic market conditions could explain the move', hypothesis:'Lower inventories, distribution bottlenecks, currency movements or a policy change could contribute to the price rise. The explanation should compare these possibilities against production and demand data.', evidence:['Market prices and stock levels','Policy, currency and demand indicators'], confidence:73, limitation:'Several explanations fit the same price pattern; causality is not established.'}
];
export function explanationFor(id, country) {
 if(!country)return null;
 const scenario=scenarios[Number(id)%scenarios.length];
 const baseline=260+(Number(id)%7)*15;
 return {...scenario,price:{commodity:'Wheat · illustrative local wholesale',currency:'USD',unit:'tonne',previous:baseline,current:Math.round(baseline*(1+country.wheat/100)),changePct:country.wheat,period:'vs. previous 30-day demo period'},method:'The future model should compare the observed price change with historical patterns and country exposure, rank plausible explanations, and attach supporting sources. This preview uses authored fixtures; no inference has run.',sources:scenario.evidence.map((name,i)=>({id:`${id}-${i}`,name,status:'Not connected',observedAt:null,url:null})),modelVersion:null,generatedAt:null};
}
export function demoAnswer(question, context) {
 const {country,horizon,risk,explanation}=context;
 if(!explanation)return `There is no demo prediction for ${country}. Select a covered country to explore its sample data. Live model questions are not connected yet.`;
 const q=question.toLowerCase();
 if(/confiden|certain|sure|accur|reliab/.test(q))return `The sample confidence score for ${country} is ${explanation.confidence}%. It is a separate, uncalibrated placeholder—not a measured probability that the forecast is correct. ${explanation.limitation} The ${risk}% figure describes the illustrative risk of increased food insecurity over ${horizon} days, not confidence.`;
 if(/source|where.*data|evidence|provenance/.test(q))return `No live sources are connected. The example evidence fields for ${country} are: ${explanation.sources.map(s=>s.name).join('; ')}. A live response should cite the exact records, observation dates, and model version used. All values in this preview are synthetic.`;
 if(/price|cost|wheat/.test(q))return `For ${country}, the synthetic wheat-price example moves from $${explanation.price.previous} to $${explanation.price.current} per tonne, a +${explanation.price.changePct}% change before rounding, versus the previous 30-day demo period. This price observation is separate from the ${horizon}-day forecast. Possible explanation: ${explanation.hypothesis}`;
 if(/why|reason|explain|predict|happen|hormuz|factor/.test(q))return `${country} has an illustrative ${risk}% risk over ${horizon} days. ${explanation.hypothesis} ${explanation.method}`;
 return `This demo chat can explain ${country}'s sample price, possible reasons, confidence and source fields. It cannot yet reason freely or query a trained model. Try “Why this prediction?”, “How confident is it?” or “What are the sources?” Your question has not been sent to an LLM.`;
}
