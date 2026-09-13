import OpenAI from 'openai';

const client = new OpenAI();

export default async function handler(request, response) {
  if (request.method !== 'POST') return response.status(405).json({ error: 'Method not allowed' });
  try {
    const { question, prediction, country, history = [] } = request.body || {};
    if (typeof question !== 'string' || !question.trim()) return response.status(400).json({ error: 'Question is required' });
    if (!prediction || !country) return response.status(400).json({ error: 'A model prediction and country are required' });
    const context = JSON.stringify({ country, prediction: {
      phase: prediction.predicted_phase, phaseLabel: prediction.phase_label,
      cutoff: prediction.cutoff, targetMonth: prediction.target_month,
      rationale: prediction.rationale, recommendedActions: prediction.recommended_actions,
      validOutput: prediction.valid_output,
    }});
    const safeHistory = Array.isArray(history) ? history.slice(-6).filter(item => item && (item.role === 'user' || item.role === 'assistant') && typeof item.content === 'string') : [];
    const result = await client.responses.create({
      model: process.env.OPENAI_MODEL || 'gpt-5-mini', store: false,
      instructions: `You are Ask OpenRelief, a careful food-security research assistant. Answer only from the supplied model context. Explain that IPC phase 1–5 is a categorical severity class, not a probability or confidence score. The prediction is a historical held-out district sample, not a current national forecast. Treat rationale statements as hypotheses, never proven causes. If the context does not answer the question, say what is missing. Do not invent prices, sources, current events, locations, or certainty. Keep the answer concise and useful.\n\nMODEL CONTEXT:\n${context}`,
      input: [...safeHistory, { role: 'user', content: question.trim() }],
    });
    return response.status(200).json({ answer: result.output_text || 'The model did not return a text answer.', model: result.model });
  } catch (error) {
    console.error('OpenRelief chat error', error?.message || error);
    return response.status(502).json({ error: 'The OpenAI answer service is temporarily unavailable.' });
  }
}
