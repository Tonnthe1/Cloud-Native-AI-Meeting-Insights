import axios from "axios";

export type MeetingStatus = "queued" | "processing" | "completed" | "failed";

export interface Meeting {
  id: number;
  filename: string;
  created_at: string;
  status: MeetingStatus;
  error_message?: string | null;
  summary?: string | null;
  language?: string | null;
  duration_seconds?: number | null;
  keywords?: string[] | null;
}

export interface MeetingDetail extends Meeting {
  transcript?: string | null;
}

export interface AnalyzeMeetingResponse {
  status: MeetingStatus;
  meeting_id: number;
  job_id?: string;
  message?: string;
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Only needed when the backend sets API_KEY. NEXT_PUBLIC_* values are
// embedded in the browser bundle, so this is a shared secret, not real auth.
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

const client = axios.create({
  baseURL: API_URL,
  headers: API_KEY ? { "X-API-Key": API_KEY } : undefined,
});

export function isPending(status: MeetingStatus): boolean {
  return status === "queued" || status === "processing";
}

/** Turn an API or network error into a message worth showing to users. */
export function getErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    if (!err.response) {
      return `Cannot reach the API at ${API_URL}. Is the backend running?`;
    }
    const detail = err.response.data?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: [{ msg: "...", ... }]
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ") || fallback;
    }
    return err.message || fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export const meetingService = {
  async getMeetings(): Promise<Meeting[]> {
    const { data } = await client.get<Meeting[]>("/meetings");
    return data;
  },

  async searchMeetings(query: string): Promise<Meeting[]> {
    const { data } = await client.get<Meeting[]>("/search", { params: { q: query } });
    return data;
  },

  async getMeeting(id: number): Promise<MeetingDetail> {
    const { data } = await client.get<MeetingDetail>(`/meetings/${id}`);
    return data;
  },

  async deleteMeeting(id: number): Promise<void> {
    await client.delete(`/meetings/${id}`);
  },

  /** Upload a recording; onUploadProgress receives 0-100 as bytes are sent. */
  async analyzeMeeting(
    file: File,
    onUploadProgress?: (percent: number) => void,
  ): Promise<AnalyzeMeetingResponse> {
    const form = new FormData();
    form.append("file", file);
    const { data } = await client.post<AnalyzeMeetingResponse>("/analyze-meeting", form, {
      onUploadProgress: (event) => {
        if (onUploadProgress && event.total) {
          onUploadProgress(Math.round((event.loaded / event.total) * 100));
        }
      },
    });
    return data;
  },
};
