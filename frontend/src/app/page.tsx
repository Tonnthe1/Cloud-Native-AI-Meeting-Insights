"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  MagnifyingGlassIcon,
  PlusIcon,
} from "@heroicons/react/24/outline";

import { meetingService } from "@/lib/api";
import type { Meeting } from "@/lib/api";

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected request failure";
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function MeetingCardSkeleton() {
  return (
    <div className="animate-pulse rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-3 h-5 w-3/4 rounded bg-gray-200" />
      <div className="mb-4 h-4 w-1/2 rounded bg-gray-200" />
      <div className="space-y-2">
        <div className="h-3 rounded bg-gray-200" />
        <div className="h-3 w-5/6 rounded bg-gray-200" />
        <div className="h-3 w-4/6 rounded bg-gray-200" />
      </div>
    </div>
  );
}

function MeetingCard({ meeting }: { meeting: Meeting }) {
  const router = useRouter();
  const summary = meeting.summary?.trim() || "No summary available";
  const excerpt = summary.length > 150 ? `${summary.slice(0, 150)}...` : summary;

  return (
    <button
      type="button"
      onClick={() => router.push(`/meeting/${meeting.id}`)}
      className="group w-full cursor-pointer rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-shadow duration-200 hover:shadow-md"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-900 transition-colors group-hover:text-blue-600">
          {meeting.filename}
        </h2>
        {meeting.duration_seconds != null ? (
          <span className="shrink-0 rounded bg-gray-100 px-2 py-1 text-sm text-gray-500">
            {Math.round(meeting.duration_seconds / 60)}m
          </span>
        ) : null}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2 text-sm text-gray-500">
        <span>{formatDate(meeting.created_at)}</span>
        {meeting.language ? (
          <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-800">
            {meeting.language.toUpperCase()}
          </span>
        ) : null}
        {meeting.status ? (
          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
            {meeting.status}
          </span>
        ) : null}
      </div>

      <p className="mb-4 text-sm leading-relaxed text-gray-700">{excerpt}</p>

      {meeting.keywords?.length ? (
        <div className="flex flex-wrap gap-1">
          {meeting.keywords.slice(0, 4).map((keyword) => (
            <span
              key={keyword}
              className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-600"
            >
              {keyword}
            </span>
          ))}
          {meeting.keywords.length > 4 ? (
            <span className="text-xs text-gray-500">
              +{meeting.keywords.length - 4} more
            </span>
          ) : null}
        </div>
      ) : null}
    </button>
  );
}

export default function Home() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [searchResults, setSearchResults] = useState<Meeting[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    try {
      setSearchResults(await meetingService.searchMeetings(query));
    } catch (requestError: unknown) {
      console.error("Search failed", requestError);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadMeetings = async () => {
      try {
        const data = await meetingService.getMeetings();
        if (!cancelled) {
          setMeetings(data);
          setError(null);
        }
      } catch (requestError: unknown) {
        if (!cancelled) setError(getErrorMessage(requestError));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void loadMeetings();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void handleSearch(searchQuery);
    }, 300);
    return () => window.clearTimeout(timeoutId);
  }, [handleSearch, searchQuery]);

  const retryFetchMeetings = async () => {
    setLoading(true);
    setError(null);
    try {
      setMeetings(await meetingService.getMeetings());
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  const showingSearchResults = searchQuery.trim().length > 0;
  const displayedMeetings = showingSearchResults ? searchResults : meetings;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Meeting Dashboard</h1>
          <p className="mt-1 text-gray-600">{meetings.length} meetings analyzed</p>
        </div>
        <Link
          href="/upload"
          className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          <PlusIcon className="mr-2 h-5 w-5" />
          Upload New Meeting
        </Link>
      </header>

      <div className="relative">
        <MagnifyingGlassIcon className="pointer-events-none absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
        <input
          type="search"
          aria-label="Search meetings"
          placeholder="Search meetings by content, filename, or keywords..."
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          className="block w-full rounded-lg border border-gray-300 bg-white py-3 pl-10 pr-10 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {isSearching ? (
          <div className="absolute right-3 top-4 h-4 w-4 animate-spin rounded-full border-b-2 border-blue-600" />
        ) : null}
      </div>

      {showingSearchResults ? (
        <p className="text-sm text-gray-600">
          {isSearching
            ? "Searching..."
            : `${searchResults.length} matching meeting${searchResults.length === 1 ? "" : "s"}`}
        </p>
      ) : null}

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <strong>Error:</strong> {error}
          <button
            type="button"
            onClick={() => void retryFetchMeetings()}
            className="ml-3 text-red-600 underline hover:text-red-500"
          >
            Try again
          </button>
        </div>
      ) : null}

      {loading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <MeetingCardSkeleton key={index} />
          ))}
        </div>
      ) : null}

      {!loading && !error && displayedMeetings.length === 0 ? (
        <section className="py-12 text-center">
          <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-gray-100">
            {showingSearchResults ? (
              <MagnifyingGlassIcon className="h-12 w-12 text-gray-400" />
            ) : (
              <PlusIcon className="h-12 w-12 text-gray-400" />
            )}
          </div>
          <h2 className="mb-2 text-lg font-medium text-gray-900">
            {showingSearchResults ? "No meetings found" : "No meetings yet"}
          </h2>
          <p className="mb-6 text-gray-500">
            {showingSearchResults
              ? `No meetings match ${searchQuery}.`
              : "Upload your first recording to generate private, structured meeting insights."}
          </p>
          {showingSearchResults ? (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="text-blue-600 underline hover:text-blue-500"
            >
              Clear search
            </button>
          ) : (
            <Link
              href="/upload"
              className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <PlusIcon className="mr-2 h-5 w-5" />
              Upload Your First Meeting
            </Link>
          )}
        </section>
      ) : null}

      {!loading && !error && displayedMeetings.length > 0 ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {displayedMeetings.map((meeting) => (
            <MeetingCard key={meeting.id} meeting={meeting} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
