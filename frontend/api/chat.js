import OpenAI from 'openai';

const client = new OpenAI();

export default async function handler(request, response) {
  if (request.method !== 'POST') return response.status(405).json({error:'Method not allowed'});
  try {
    const {question, country, prediction, history=[]} = request.body || {};
    if (!question?.trim() || !country || !prediction) return response.status(400).json({error:'Question, country and prediction are required'});
    const context = JSON.stringify({country, prediction:{phase:prediction.predicted_phase, label:prediction.phase_label, cutoff:prediction.cutoff, targetMonth:prediction.target_month, rationale:prediction.rationale, actions:prediction.recommended_actions, sampleId:prediction.sample_id}});
    const safeHistory = Array.isArray(history) ? history.slice(-6).filter(m=>m && ['user','assistant'].includes(m.role) && typeof m.content==='string') : [];
    const result = await client.responses.create({
      model: process.env.OPENAI_MODEL || 'gpt-5-mini', store:false,
      instructions:`You are Ask OpenRelief. Answer the user's question using only the supplied OpenRelief model context. The context is a historical held-out district sample, not a current national forecast. IPC phase 1–5 is a categorical severity class, not a hunger probability or confidence score. The model rationale contains hypotheses, not proven causes. Do not invent data, current events, sources, prices, locations, or certainty. If the context cannot answer, say what is missing. Keep the response concise.\n\nOPENRELIEF CONTEXT:\n${context}`,
      input:[...safeHistory,{role:'user',content:question.trim()}],
    });
    return response.status(200).json({answer:result.output_text || 'No answer was returned.'});
  } catch (error) {
    console.error('OpenRelief local chat error',error?.message || error);
    return response.status(502).json({error:'OpenAI chat is unavailable locally.'});
  }
}
