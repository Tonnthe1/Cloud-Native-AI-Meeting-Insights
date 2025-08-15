"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { meetingService, MeetingDetail } from "@/lib/api";
import { 
  ArrowLeftIcon, 
  TrashIcon, 
  CalendarIcon,
  ClockIcon,
  LanguageIcon,
  TagIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon
} from "@heroicons/react/24/outline";

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
  isDeleting 
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  filename: string;
  isDeleting: boolean;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <div className="flex items-center mb-4">
          <ExclamationTriangleIcon className="h-6 w-6 text-red-600 mr-3" />
          <h3 className="text-lg font-semibold text-gray-900">Delete Meeting</h3>
        </div>
        
        <p className="text-gray-600 mb-6">
          Are you sure you want to delete "{filename}"? This action cannot be undone.
        </p>
        
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

  useEffect(() => {
    if (id) {
      fetchMeeting();
    }
  }, [id]);

  const fetchMeeting = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await meetingService.getMeeting(parseInt(id));
      setMeeting(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to fetch meeting details");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      await meetingService.deleteMeeting(parseInt(id));
      router.push("/");
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to delete meeting");
      setShowDeleteModal(false);
    } finally {
      setIsDeleting(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
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
            className="mt-1 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors duration-200"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{meeting.filename}</h1>
            <p className="text-gray-600 mt-1">Meeting Details</p>
          </div>
        </div>
        
        <button
          onClick={() => setShowDeleteModal(true)}
          className="inline-flex items-center px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors duration-200"
        >
          <TrashIcon className="h-4 w-4 mr-2" />
          Delete Meeting
        </button>
      </div>

      {/* Meeting Metadata */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center text-sm text-gray-500 mb-1">
            <CalendarIcon className="h-4 w-4 mr-1" />
            Date
          </div>
          <div className="font-semibold text-gray-900">
            {formatDate(meeting.created_at)}
          </div>
        </div>

        {meeting.duration_seconds && (
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
            {meeting.keywords.map((keyword, index) => (
              <span
                key={index}
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
            <p className="text-gray-500 italic">No summary available</p>
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
            <p className="text-gray-500 italic">No transcript available</p>
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
      />
    </div>
  );
}