"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { meetingService, MeetingDetail, getErrorMessage, isPending } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";
import { 
  ArrowLeftIcon, 
  ArrowPathIcon,
  TrashIcon, 
  CalendarIcon,
  ClockIcon,
  LanguageIcon,
  TagIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon
} from "@heroicons/react/24/outline";

// How often to check on a meeting that's still being processed.
const POLL_INTERVAL_MS = 3000;

// Loading skeleton
function DetailSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-3/4"></div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-6 bg-gray-200 rounded"></div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            {[...Array(12)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Delete confirmation modal
function DeleteModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  filename,
  isDeleting,
  error
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  filename: string;
  isDeleting: boolean;
  error: string | null;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div
        className="bg-white rounded-lg max-w-md w-full p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-meeting-title"
      >
        <div className="flex items-center mb-4">
          <ExclamationTriangleIcon className="h-6 w-6 text-red-600 mr-3" />
          <h3 id="delete-meeting-title" className="text-lg font-semibold text-gray-900">Delete Meeting</h3>
        </div>
        
        <p className="text-gray-600 mb-6 break-words">
          Are you sure you want to delete &ldquo;{filename}&rdquo;? This action cannot be undone.
        </p>

        {error && (
          <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3 mb-4" role="alert">
            {error}
          </p>
        )}
        
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors duration-200 disabled:opacity-50 flex items-center"
          >
            {isDeleting && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
            )}
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MeetingDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchMeeting = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setMeeting(await meetingService.getMeeting(parseInt(id)));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to fetch meeting details"));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchMeeting();
    }
  }, [id, fetchMeeting]);

  // While the meeting is queued or processing, refresh it in the background
  // so the transcript and summary appear as soon as they're ready.
  const pending = meeting ? isPending(meeting.status) : false;
  useEffect(() => {
    if (!pending) return;
    const intervalId = setInterval(() => {
      meetingService.getMeeting(parseInt(id)).then(setMeeting).catch(() => {
        // Transient failures are fine; the next poll will retry.
      });
    }, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [pending, id]);

  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      setDeleteError(null);
      await meetingService.deleteMeeting(parseInt(id));
      router.push("/");
    } catch (err) {
      setDeleteError(getErrorMessage(err, "Failed to delete meeting"));
    } finally {
      setIsDeleting(false);
    }
  };

  if (loading) {
    return <DetailSkeleton />;
  }

  if (error || !meeting) {
    return (
      <div className="text-center py-12">
        <div className="mx-auto h-24 w-24 bg-red-100 rounded-full flex items-center justify-center mb-6">
          <ExclamationTriangleIcon className="h-12 w-12 text-red-500" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Meeting</h3>
        <p className="text-gray-500 mb-6">
          {error || "Meeting not found"}
        </p>
        <div className="space-x-3">
          <button
            onClick={() => router.push("/")}
            className="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors duration-200"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Meetings
          </button>
          <button
            onClick={fetchMeeting}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors duration-200"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-start space-x-4">
          <button
            onClick={() => router.push("/")}
            aria-label="Back to meetings"
            className="mt-1 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors duration-200"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div className="min-w-0">
            <h1 className="text-3xl font-bold text-gray-900 break-all">{meeting.filename}</h1>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-gray-600">Meeting Details</p>
              <StatusBadge status={meeting.status} />
            </div>
          </div>
        </div>
        
        <button
          onClick={() => {
            setDeleteError(null);
            setShowDeleteModal(true);
          }}
          className="inline-flex items-center justify-center px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors duration-200"
        >
          <TrashIcon className="h-4 w-4 mr-2" />
          Delete Meeting
        </button>
      </div>

      {/* Processing Status */}
      {pending && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center text-sm text-amber-800">
          <ArrowPathIcon className="h-5 w-5 mr-2 shrink-0 animate-spin" />
          {meeting.status === "queued"
            ? "Waiting for a worker to pick up this recording."
            : "Transcribing and summarizing this recording."}{" "}
          This page updates automatically.
        </div>
      )}
      {meeting.status === "failed" && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start text-sm text-red-700" role="alert">
          <ExclamationTriangleIcon className="h-5 w-5 mr-2 shrink-0" />
          <div>
            <strong>Processing failed.</strong>{" "}
            {meeting.error_message || "The recording could not be processed."}
          </div>
        </div>
      )}

      {/* Meeting Metadata */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center text-sm text-gray-500 mb-1">
            <CalendarIcon className="h-4 w-4 mr-1" />
            Date
          </div>
          <div className="font-semibold text-gray-900">
            {formatDate(meeting.created_at, "long")}
          </div>
        </div>

        {meeting.duration_seconds != null && (
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center text-sm text-gray-500 mb-1">
              <ClockIcon className="h-4 w-4 mr-1" />
              Duration
            </div>
            <div className="font-semibold text-gray-900">
              {formatDuration(meeting.duration_seconds)}
            </div>
          </div>
        )}

        {meeting.language && (
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center text-sm text-gray-500 mb-1">
              <LanguageIcon className="h-4 w-4 mr-1" />
              Language
            </div>
            <div className="font-semibold text-gray-900">
              {meeting.language.toUpperCase()}
            </div>
          </div>
        )}

        {meeting.keywords && meeting.keywords.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center text-sm text-gray-500 mb-1">
              <TagIcon className="h-4 w-4 mr-1" />
              Keywords
            </div>
            <div className="font-semibold text-gray-900">
              {meeting.keywords.length} tags
            </div>
          </div>
        )}
      </div>

      {/* Keywords */}
      {meeting.keywords && meeting.keywords.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Keywords</h2>
          <div className="flex flex-wrap gap-2">
            {meeting.keywords.map((keyword) => (
              <span
                key={keyword}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Summary */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <DocumentTextIcon className="h-5 w-5 mr-2" />
            Summary
          </h2>
          {meeting.summary ? (
            <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
              {meeting.summary}
            </div>
          ) : (
            <p className="text-gray-500 italic">{pending ? "Summary will appear here once processing finishes." : "No summary available"}</p>
          )}
        </div>

        {/* Transcript */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <DocumentTextIcon className="h-5 w-5 mr-2" />
            Transcript
          </h2>
          {meeting.transcript ? (
            <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto">
              {meeting.transcript}
            </div>
          ) : (
            <p className="text-gray-500 italic">{pending ? "Transcript will appear here once processing finishes." : "No transcript available"}</p>
          )}
        </div>
      </div>

      {/* Delete Modal */}
      <DeleteModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDelete}
        filename={meeting.filename}
        isDeleting={isDeleting}
        error={deleteError}
      />
    </div>
  );
}