export interface EventCreate {
  name: string;
  description: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  author_login: string;
}

export interface ParticipantJoin {
  login: string;
}

export interface BlockerRangeCreate {
  start_date: string;
  end_date: string;
}

export interface BlockerCreate {
  login: string;
  dates?: string[];
  ranges?: BlockerRangeCreate[];
}

export interface Blocker {
  id: number;
  date: string;
}

export interface Participant {
  id: number;
  login: string;
  blockers: Blocker[];
}

export interface EventRead {
  code: string;
  name: string;
  description: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  created_by: string;
  created_at: string;
  participants: Participant[];
}

export interface Suggestion {
  start_date: string;
  end_date: string;
  duration_days: number;
  requested_duration_days: number;
  shortened: boolean;
}

export interface SuggestionResponse {
  event_code: string;
  requested_duration_days: number;
  used_duration_days: number | null;
  shortened: boolean;
  suggestions: Suggestion[];
}
