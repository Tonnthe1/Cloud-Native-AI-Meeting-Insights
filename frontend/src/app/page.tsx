"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { meetingService, Meeting, getErrorMessage, isPending } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";
import { MagnifyingGlassIcon, PlusIcon } from "@heroicons/react/24/outline";

// How often to refresh the list while any meeting is still being processed.
const POLL_INTERVAL_MS = 5000;

function MeetingCardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
      <div className="h-5 bg-gray-200 rounded w-3/4 mb-3"></div>
      <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
      <div className="space-y-2">
        <div className="h-3 bg-gray-200 rounded"></div>
        <div className="h-3 bg-gray-200 rounded w-5/6"></div>
        <div className="h-3 bg-gray-200 rounded w-4/6"></div>
      </div>
    </div>
  );
}

function SummaryExcerpt({ meeting }: { meeting: Meeting }) {
  if (isPending(meeting.status)) {
    return <p className="text-gray-500 text-sm italic mb-4">Transcribing and summarizing…</p>;
  }
  if (meeting.status === "failed") {
    return (
      <p className="text-red-700 text-sm mb-4 line-clamp-3">
        Processing failed{meeting.error_message ? `: ${meeting.error_message}` : ""}
      </p>
    );
  }
  const summary = meeting.summary;
  return (
    <p className="text-gray-700 text-sm leading-relaxed mb-4">
      {!summary
        ? "No summary available"
        : summary.length > 150
          ? summary.substring(0, 150) + "..."
          : summary}
    </p>
  );
}

function MeetingCard({ meeting }: { meeting: Meeting }) {
  return (
    <Link
      href={`/meeting/${meeting.id}`}
      className="block bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200 group focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors break-all">
          {meeting.filename}
        </h3>
        {meeting.duration_seconds != null && (
          <span className="shrink-0 text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {formatDuration(meeting.duration_seconds)}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500 mb-4">
        <span>{formatDate(meeting.created_at)}</span>
        {meeting.language && (
          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
            {meeting.language.toUpperCase()}
          </span>
        )}
        {meeting.status !== "completed" && <StatusBadge status={meeting.status} />}
      </div>

      <SummaryExcerpt meeting={meeting} />

      {meeting.keywords && meeting.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {meeting.keywords.slice(0, 4).map((keyword) => (
            <span key={keyword} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
              {keyword}
            </span>
          ))}
          {meeting.keywords.length > 4 && (
            <span className="text-xs text-gray-500">+{meeting.keywords.length - 4} more</span>
          )}
        </div>
      )}
    </Link>
  );
}

export default function Home() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<Meeting[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  const fetchMeetings = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setMeetings(await meetingService.getMeetings());
    } catch (err) {
      setError(getErrorMessage(err, "Failed to fetch meetings"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMeetings();
  }, [fetchMeetings]);

  // Keep refreshing quietly while uploads are still being processed.
  const hasPending = meetings.some((m) => isPending(m.status));
  useEffect(() => {
    if (!hasPending) return;
    const intervalId = setInterval(() => {
      meetingService.getMeetings().then(setMeetings).catch(() => {
        // Transient failures are fine; the next poll will retry.
      });
    }, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [hasPending]);

  // Debounced search; responses for outdated queries are ignored.
  useEffect(() => {
    const query = searchQuery.trim();
    setSearchError(null);
    if (!query) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    let cancelled = false;
    setIsSearching(true);
    const timeoutId = setTimeout(async () => {
      try {
        const results = await meetingService.searchMeetings(query);
        if (!cancelled) setSearchResults(results);
      } catch (err) {
        if (!cancelled) {
          setSearchResults([]);
          setSearchError(getErrorMessage(err, "Search failed"));
        }
      } finally {
        if (!cancelled) setIsSearching(false);
      }
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [searchQuery]);

  const isShowingSearchResults = searchQuery.trim().length > 0;
  const displayedMeetings = isShowingSearchResults ? searchResults : meetings;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Meeting Dashboard</h1>
          <p className="text-gray-600 mt-1">
            {meetings.length} meeting{meetings.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Link
          href="/upload"
          className="inline-flex items-center justify-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors duration-200"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Upload New Meeting
        </Link>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="search"
          aria-label="Search meetings"
          placeholder="Search meetings by content, filename, or keywords..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="block w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
        {isSearching && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          </div>
        )}
      </div>

      {/* Search Results Info */}
      {isShowingSearchResults && (
        <div className={`text-sm ${searchError ? "text-red-700" : "text-gray-600"}`}>
          {isSearching
            ? "Searching..."
            : searchError
              ? searchError
              : `Found ${searchResults.length} meeting${searchResults.length !== 1 ? "s" : ""} matching "${searchQuery.trim()}"`}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-sm text-red-700">
            <strong>Error:</strong> {error}
          </div>
          <button
            onClick={fetchMeetings}
            className="mt-3 text-sm text-red-600 hover:text-red-500 underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <MeetingCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && !isSearching && !searchError && displayedMeetings.length === 0 && (
        <div className="text-center py-12">
          <div className="mx-auto h-24 w-24 bg-gray-100 rounded-full flex items-center justify-center mb-6">
            {isShowingSearchResults ? (
              <MagnifyingGlassIcon className="h-12 w-12 text-gray-400" />
            ) : (
              <PlusIcon className="h-12 w-12 text-gray-400" />
            )}
          </div>
          {isShowingSearchResults ? (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No meetings found</h3>
              <p className="text-gray-500 mb-6">
                No meetings match your search for &ldquo;{searchQuery.trim()}&rdquo;
              </p>
              <button
                onClick={() => setSearchQuery("")}
                className="text-blue-600 hover:text-blue-500 underline"
              >
                Clear search
              </button>
            </div>
          ) : (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No meetings yet</h3>
              <p className="text-gray-500 mb-6">
                Upload your first meeting recording to get started with AI-powered insights.
              </p>
              <Link
                href="/upload"
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors duration-200"
              >
                <PlusIcon className="h-5 w-5 mr-2" />
                Upload Your First Meeting
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Meeting Cards */}
      {!loading && !error && displayedMeetings.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayedMeetings.map((meeting) => (
            <MeetingCard key={meeting.id} meeting={meeting} />
          ))}
        </div>
      )}
    </div>
  );
}
