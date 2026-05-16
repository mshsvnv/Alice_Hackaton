/**
 * API-клиент для взаимодействия с бэкендом FastAPI.
 */

import type {
  ProfileCreate,
  ProfileResponse,
  DocumentInfo,
  DisabilityType,
  TestCreate,
  TestResponse,
  TestListItem,
  TestResultCreate,
  TestResultResponse,
} from './types';

const BASE_URL = '/api/v1';

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> ?? {}),
  };

  // Если тело — не FormData, ставим JSON-Content-Type
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `HTTP ${res.status}`);
  }

  // Для 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json();
}

// ──────────────── Auth ────────────────

export const authApi = {
  register: (data: ProfileCreate) =>
    request<ProfileResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getProfile: (profileId: string) =>
    request<ProfileResponse>(`/auth/profile/${profileId}`),
};

// ──────────────── Profiles ────────────────

export const profileApi = {
  list: () => request<ProfileResponse[]>('/profiles/'),

  get: (id: string) => request<ProfileResponse>(`/profiles/${id}`),

  update: (id: string, data: Partial<ProfileCreate>) =>
    request<ProfileResponse>(`/profiles/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<{ status: string }>(`/profiles/${id}`, { method: 'DELETE' }),
};

// ──────────────── Documents ────────────────

export const documentApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<DocumentInfo>('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  },

  list: () => request<DocumentInfo[]>('/documents/'),

  get: (id: string) => request<DocumentInfo>(`/documents/${id}`),

  parseTest: (text: string) =>
    request<Record<string, unknown>>('/documents/parse-test', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  generateQuestions: (text: string, complexity: string = 'simple', count: number = 5) =>
    request<Record<string, unknown>>('/documents/generate-questions', {
      method: 'POST',
      body: JSON.stringify({ text, complexity, count }),
    }),
};

// ──────────────── Tests ────────────────

export const testApi = {
  create: (data: TestCreate) =>
    request<TestResponse>('/tests/create', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createFromDocument: (documentId: string, title: string, authorId: string, disabilityType: DisabilityType, isPublic = true) => {
    const params = new URLSearchParams({
      document_id: documentId,
      title,
      author_id: authorId,
      disability_type: disabilityType,
      is_public: String(isPublic),
    });
    return request<TestResponse>(`/tests/create-from-document?${params}`, {
      method: 'POST',
    });
  },

  createFromText: (text: string, title: string, authorId: string, disabilityType: DisabilityType, isPublic = true) => {
    const params = new URLSearchParams({
      text,
      title,
      author_id: authorId,
      disability_type: disabilityType,
      is_public: String(isPublic),
    });
    return request<TestResponse>(`/tests/create-from-text?${params}`, {
      method: 'POST',
    });
  },

  listPublic: () => request<TestListItem[]>('/tests/public'),

  listByAuthor: (authorId: string) => request<TestListItem[]>(`/tests/by-author/${authorId}`),

  get: (id: string) => request<TestResponse>(`/tests/${id}`),

  getByShareLink: (shareLink: string) => request<TestResponse>(`/tests/share/${shareLink}`),

  saveResult: (data: TestResultCreate) =>
    request<TestResultResponse>('/tests/results', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getUserResults: (profileId: string) =>
    request<TestResultResponse[]>(`/tests/results/${profileId}`),
};

// ──────────────── Voice ────────────────

export const voiceApi = {
  /** Проверяет доступность голосового интерфейса */
  getStatus: () =>
    fetch('/api/v1/voice/status').then((res) => res.json()),

  /** Синтез речи (TTS) — возвращает Blob с аудио */
  synthesize: async (text: string, voice = 'alena', speed = 1.0): Promise<Blob> => {
    const formData = new FormData();
    formData.append('text', text);
    formData.append('voice', voice);
    formData.append('speed', String(speed));

    const res = await fetch('/api/v1/voice/tts', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) throw new Error(`TTS error: ${res.status}`);
    return res.blob();
  },

  /** Распознавание речи (ASR) — отправляет аудиофайл */
  recognize: async (audioBlob: Blob, language = 'ru-RU'): Promise<{ text: string }> => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.ogg');
    formData.append('language', language);

    const res = await fetch('/api/v1/voice/asr', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) throw new Error(`ASR error: ${res.status}`);
    return res.json();
  },
};
