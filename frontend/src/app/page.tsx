"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { meetingService, Meeting } from "@/lib/api";
import { MagnifyingGlassIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useRouter } from "next/navigation";

// Loading skeleton component
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

// Meeting card component
function MeetingCard({ meeting }: { meeting: Meeting }) {
  const router = useRouter();
  
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getSummaryExcerpt = (summary: string | null | undefined) => {
    if (!summary) return "No summary available";
    return summary.length > 150 ? summary.substring(0, 150) + "..." : summary;
  };

  const handleCardClick = () => {
    router.push(`/meeting/${meeting.id}`);
  };

  return (
    <div 
      onClick={handleCardClick}
      className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200 cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
          {meeting.filename}
        </h3>
        {meeting.duration_seconds && (
          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {Math.round(meeting.duration_seconds / 60)}m
          </span>
        )}
      </div>
      
      <p className="text-sm text-gray-500 mb-4">
        {formatDate(meeting.created_at)}
        {meeting.language && (
          <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
            {meeting.language.toUpperCase()}
          </span>
        )}
      </p>
      
      <p className="text-gray-700 text-sm leading-relaxed mb-4">
        {getSummaryExcerpt(meeting.summary)}
      </p>
      
      {meeting.keywords && meeting.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {meeting.keywords.slice(0, 4).map((keyword, index) => (
            <span 
              key={index}
              className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded"
            >
              {keyword}
            </span>
          ))}
          {meeting.keywords.length > 4 && (
            <span className="text-xs text-gray-500">+{meeting.keywords.length - 4} more</span>
          )}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<Meeting[]>([]);
  
  const fetchMeetings = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await meetingService.getMeetings();
      setMeetings(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to fetch meetings");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    try {
      setIsSearching(true);
      const results = await meetingService.searchMeetings(query);
      setSearchResults(results);
    } catch (err: any) {
      console.error("Search failed:", err);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  useEffect(() => {
    fetchMeetings();
  }, [fetchMeetings]);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      handleSearch(searchQuery);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery, handleSearch]);

  const displayedMeetings = searchQuery.trim() ? searchResults : meetings;
  const isShowingSearchResults = searchQuery.trim().length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Meeting Dashboard</h1>
          <p className="text-gray-600 mt-1">
            {meetings.length} meetings analyzed
          </p>
        </div>
        <Link
          href="/upload"
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors duration-200"
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
          type="text"
          placeholder="Search meetings by content, filename, or keywords..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
        {isSearching && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          </div>
        )}
      </div>

      {/* Search Results Info */}
      {isShowingSearchResults && (
        <div className="text-sm text-gray-600">
          {isSearching ? (
            "Searching..."
          ) : (
            `Found ${searchResults.length} meeting${searchResults.length !== 1 ? 's' : ''} matching "${searchQuery}"`
          )}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="text-sm text-red-700">
              <strong>Error:</strong> {error}
            </div>
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
      {!loading && !error && displayedMeetings.length === 0 && (
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
                No meetings match your search for "{searchQuery}"
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
