"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  ClockIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  QuestionMarkCircleIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { meetingService, MeetingDetail } from "@/lib/api";

function Section({
  title,
  items,
  icon,
}: {
  title: string;
  items?: string[] | null;
  icon: React.ReactNode;
}) {
  if (!items?.length) return null;
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-6">
      <h2 className="mb-4 flex items-center text-lg font-semibold text-gray-900">
        <span className="mr-2">{icon}</span>
        {title}
      </h2>
      <ul className="space-y-2 text-sm text-gray-700">
        {items.map((item, index) => (
          <li key={`${title}-${index}`} className="flex gap-2">
            <span className="mt-1 text-gray-400">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function MeetingDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = Number(params.id);
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;

    const loadMeeting = async () => {
      try {
        const data = await meetingService.getMeeting(id);
        if (cancelled) return;
        setMeeting(data);
        setError(null);
        if (data.status === "queued" || data.status === "processing") {
          refreshTimer = setTimeout(loadMeeting, 3_000);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load meeting");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void loadMeeting();
    return () => {
      cancelled = true;
      if (refreshTimer) clearTimeout(refreshTimer);
    };
  }, [id]);

  const handleDelete = async () => {
    if (!meeting || !window.confirm(`Delete ${meeting.filename}?`)) return;
    setDeleting(true);
    try {
      await meetingService.deleteMeeting(meeting.id);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      setDeleting(false);
    }
  };

  if (loading) {
    return <div className="py-16 text-center text-gray-500">Loading meeting…</div>;
  }

  if (error || !meeting) {
    return (
      <div className="py-16 text-center">
        <ExclamationTriangleIcon className="mx-auto mb-4 h-12 w-12 text-red-500" />
        <p className="mb-4 text-red-700">{error || "Meeting not found"}</p>
        <button className="text-blue-600 underline" onClick={() => router.push("/")}>
          Back to meetings
        </button>
      </div>
    );
  }

  const insights = meeting.insights;

  return (
    <div className="space-y-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div className="flex gap-3">
          <button
            aria-label="Back"
            onClick={() => router.push("/")}
            className="mt-1 rounded p-2 text-gray-500 hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{meeting.filename}</h1>
            <div className="mt-2 flex flex-wrap gap-2 text-sm text-gray-500">
              <span>{new Date(meeting.created_at).toLocaleString()}</span>
              {meeting.duration_seconds ? (
                <span>• {Math.round(meeting.duration_seconds / 60)} min</span>
              ) : null}
              {meeting.language ? <span>• {meeting.language.toUpperCase()}</span> : null}
              {meeting.status ? <span>• {meeting.status}</span> : null}
            </div>
          </div>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="inline-flex items-center rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          <TrashIcon className="mr-2 h-4 w-4" />
          {deleting ? "Deleting…" : "Delete"}
        </button>
      </header>

      {insights ? (
        <>
          <section className="rounded-lg border border-blue-200 bg-blue-50 p-6">
            <div className="mb-2 flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-blue-950">Overview</h2>
              {insights.provider ? (
                <span className="rounded bg-white px-2 py-1 text-xs text-blue-700">
                  {insights.provider}
                </span>
              ) : null}
            </div>
            <p className="whitespace-pre-wrap text-blue-950">{insights.overview}</p>
          </section>

          {insights.action_items.length ? (
            <section className="rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="mb-4 flex items-center text-lg font-semibold text-gray-900">
                <CheckCircleIcon className="mr-2 h-5 w-5" /> Action Items
              </h2>
              <div className="space-y-3">
                {insights.action_items.map((item, index) => (
                  <div key={index} className="rounded border border-gray-200 p-4">
                    <p className="font-medium text-gray-900">{item.task}</p>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
                      {item.owner ? <span>Owner: {item.owner}</span> : null}
                      {item.due_date ? <span>Due: {item.due_date}</span> : null}
                      {item.priority ? <span>Priority: {item.priority}</span> : null}
                      <span>Status: {item.status || "open"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-2">
            <Section title="Key Points" items={insights.key_points} icon={<DocumentTextIcon className="h-5 w-5" />} />
            <Section title="Decisions" items={insights.decisions} icon={<CheckCircleIcon className="h-5 w-5" />} />
            <Section title="Risks & Blockers" items={insights.risks} icon={<ExclamationTriangleIcon className="h-5 w-5" />} />
            <Section title="Open Questions" items={insights.open_questions} icon={<QuestionMarkCircleIcon className="h-5 w-5" />} />
          </div>
        </>
      ) : (
        <section className="rounded-lg border border-gray-200 bg-white p-6">
          <div className="flex items-center text-gray-600">
            <ClockIcon className="mr-2 h-5 w-5" />
            Structured insights are not available yet.
          </div>
        </section>
      )}

      <section className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Transcript</h2>
        <div className="max-h-[32rem] overflow-y-auto whitespace-pre-wrap text-sm leading-6 text-gray-700">
          {meeting.transcript || "Transcript not available yet."}
        </div>
      </section>
    </div>
  );
}
