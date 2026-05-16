/**
 * TypeScript-типы, соответствующие Pydantic-схемам бэкенда.
 */

export type DisabilityType = 'vision' | 'motor' | 'cognitive' | 'none';

export type InteractionMode = 'voice' | 'text' | 'both';

export interface ProfileCreate {
  name: string;
  disability_type: DisabilityType;
  interaction_mode: InteractionMode;
  preferences: Record<string, unknown>;
}

export interface ProfileResponse extends ProfileCreate {
  id: string;
}

export interface TestQuestion {
  id: string;
  text: string;
  options: string[];
  correct_option_index: number;
  image_description?: string | null;
  audio_description?: string | null;
}

export interface TestCreate {
  title: string;
  author_id: string;
  disability_type: DisabilityType;
  questions: TestQuestion[];
  is_public: boolean;
}

export interface TestResponse {
  id: string;
  title: string;
  author_id: string;
  disability_type: DisabilityType;
  questions: TestQuestion[];
  is_public: boolean;
  share_link: string | null;
  created_at: string | null;
}

export interface TestListItem {
  id: string;
  title: string;
  author_id: string;
  disability_type: DisabilityType;
  is_public: boolean;
  share_link: string | null;
  questions_count: number;
  created_at: string | null;
}

export interface TestResultCreate {
  user_profile_id: string;
  test_id: string;
  answers: Record<string, unknown>[];
  score: number;
}

export interface TestResultResponse extends TestResultCreate {
  id: string;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  content_type?: string;
  extracted_text?: string;
  created_at?: string;
}

export const DISABILITY_LABELS: Record<DisabilityType, string> = {
  vision: 'Слабовидение',
  motor: 'Нарушения ОДА',
  cognitive: 'Когнитивные особенности',
  none: 'Без адаптации',
};

export const INTERACTION_LABELS: Record<InteractionMode, string> = {
  voice: 'Голосовой',
  text: 'Текстовый',
  both: 'Голосовой и текстовый',
};
