import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('session memory resolves player pronouns from the immediately prior answer', async ({ request }) => {
  const firstResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is the historical evidence for Amon-Ra St. Brown?',
      context: { page: 'Ask' },
    },
  });
  expect(firstResponse.ok()).toBeTruthy();
  const first = await firstResponse.json();

  const followResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What about him?',
      context: {
        page: 'Ask',
        session_history: [{
          role: 'assistant',
          answer: {
            intent: first.intent,
            status: first.status,
            confidence: first.confidence,
            take: first.take,
            cards: first.cards,
          },
        }],
      },
    },
  });
  expect(followResponse.ok()).toBeTruthy();
  const follow = await followResponse.json();

  expect(follow.session_reference_resolved).toBe(true);
  expect(follow.resolved_question).toContain('Amon-Ra St. Brown');
  expect(follow.intent).toBe('player_history');
  expect(follow.take).toContain('Amon-Ra St. Brown');
});

test('session memory resolves that game while structured score data remains the truth source', async ({ request }) => {
  const firstResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'Brooklyn Nets Charlotte Hornets score',
      context: { page: 'Ask' },
    },
  });
  expect(firstResponse.ok()).toBeTruthy();
  const first = await firstResponse.json();
  expect(first.cards?.[0]?.type).toBe('score');

  const followResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What about that game?',
      context: {
        page: 'Ask',
        session_history: [{
          role: 'assistant',
          answer: {
            intent: first.intent,
            status: first.status,
            confidence: first.confidence,
            take: first.take,
            cards: first.cards,
          },
        }],
      },
    },
  });
  expect(followResponse.ok()).toBeTruthy();
  const follow = await followResponse.json();

  expect(follow.session_reference_resolved).toBe(true);
  expect(follow.resolved_question).toContain('Brooklyn Nets');
  expect(follow.resolved_question).toContain('Charlotte Hornets');
  expect(follow.intent).toBe('live_score');
  expect(['LIVE', 'FINAL', 'UPCOMING']).toContain(follow.status);
});


test('session memory resolves Why by re-running the prior governed question', async ({ request }) => {
  const firstQuestion = 'Who do the Eagles play next?'
  const firstResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: firstQuestion,
      context: { page: 'Ask' },
    },
  });
  expect(firstResponse.ok()).toBeTruthy();
  const first = await firstResponse.json();

  const followResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'Why?',
      context: {
        page: 'Ask',
        session_history: [
          { role: 'user', text: firstQuestion },
          {
            role: 'assistant',
            answer: {
              intent: first.intent,
              status: first.status,
              confidence: first.confidence,
              take: first.take,
              cards: first.cards,
            },
          },
        ],
      },
    },
  });
  expect(followResponse.ok()).toBeTruthy();
  const follow = await followResponse.json();

  expect(follow.session_reference_resolved).toBe(true);
  expect(follow.resolved_question).toContain(firstQuestion);
  expect(follow.intent).toBe('schedule');
  expect(follow.status).toBe('CURRENT');
  expect(follow.why?.length).toBeGreaterThan(0);
});


test('session memory safer option can switch from higher weekly score to lower availability risk', async ({ request }) => {
  const firstQuestion = 'Start Kyle Monangai or Rhamondre Stevenson?'
  const firstResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: firstQuestion,
      context: { page: 'Ask' },
    },
  });
  expect(firstResponse.ok()).toBeTruthy();
  const first = await firstResponse.json();

  expect(first.intent).toBe('start_sit');
  expect(first.take).toContain('Kyle Monangai');
  expect(first.risk || []).toContain('Player status: QUESTIONABLE');

  const followResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'Give me the safer option',
      context: {
        page: 'Ask',
        session_history: [
          { role: 'user', text: firstQuestion },
          {
            role: 'assistant',
            answer: {
              intent: first.intent,
              status: first.status,
              confidence: first.confidence,
              take: first.take,
              cards: first.cards,
            },
          },
        ],
      },
    },
  });
  expect(followResponse.ok()).toBeTruthy();
  const follow = await followResponse.json();

  expect(follow.session_reference_resolved).toBe(true);
  expect(follow.resolved_question).toContain('safer option');
  expect(follow.intent).toBe('start_sit');
  expect(follow.take).toContain('Rhamondre Stevenson');
  expect(follow.take).toContain('Kyle Monangai');
  expect(follow.why || []).toContain('Safer ordering prioritizes lower availability risk, then existing weekly tier and research score.');
});
