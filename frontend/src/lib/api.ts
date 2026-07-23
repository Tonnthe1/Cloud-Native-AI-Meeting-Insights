import axios, { AxiosError } from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000,
  headers: API_KEY ? { "x-api-key": API_KEY } : undefined,
});

export interface ActionItem {
  task: string;
  owner?: string | null;
  due_date?: string | null;
  priority?: "low" | "medium" | "high" | null;
  status?: "open" | "in_progress" | "done" | null;
}

export interface StructuredInsights {
  overview: string;
  key_points: string[];
  decisions: string[];
  action_items: ActionItem[];
  risks: string[];
  open_questions: string[];
  provider?: string | null;
}

export interface Meeting {
  id: number;
  filename: string;
  created_at: string;
  summary?: string | null;
  language?: string | null;
  duration_seconds?: number | null;
  keywords?: string[] | null;
  status?: string | null;
}

export interface MeetingDetail extends Meeting {
  transcript?: string | null;
  insights?: StructuredInsights | null;
}

export interface AnalyzeMeetingResponse {
  status: "queued" | "processing" | "completed" | "failed";
  meeting_id: number;
  job_id?: string;
  message?: string;
}

export interface JobStatus {
  id: string;
  meeting_id: number;
  status: "queued" | "processing" | "completed" | "failed";
  attempts?: number;
  result?: Record<string, unknown>;
  last_error?: string;
}

function errorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.code === "ECONNABORTED") return "The request timed out.";
  }
  return error instanceof Error ? error.message : "Unexpected API error";
}

async function request<T>(operation: () => Promise<{ data: T }>): Promise<T> {
  try {
    const response = await operation();
    return response.data;
  } catch (error) {
    throw new Error(errorMessage(error));
  }
}

export const meetingService = {
  getMeetings(): Promise<Meeting[]> {
    return request(() => api.get<Meeting[]>("/meetings"));
  },

  getMeeting(id: number): Promise<MeetingDetail> {
    return request(() => api.get<MeetingDetail>(`/meetings/${id}`));
  },

  searchMeetings(query: string): Promise<Meeting[]> {
    return request(() =>
      api.get<Meeting[]>("/search", { params: { q: query } }),
    );
  },

  analyzeMeeting(file: File): Promise<AnalyzeMeetingResponse> {
    const form = new FormData();
    form.append("file", file);
    return request(() =>
      api.post<AnalyzeMeetingResponse>("/analyze-meeting", form, {
        headers: { "Content-Type": "multipart/form-data" },
      }),
    );
  },

  getJobStatus(jobId: string): Promise<JobStatus> {
    return request(() => api.get<JobStatus>(`/job-status/${jobId}`));
  },

  deleteMeeting(id: number): Promise<{ ok: boolean }> {
    return request(() => api.delete<{ ok: boolean }>(`/meetings/${id}`));
  },
};
