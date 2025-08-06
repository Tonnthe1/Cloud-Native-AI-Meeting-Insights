'use client'

import { useEffect, useState } from "react";
import axios from "axios";

type Meeting = {
  id: number;
  filename: string;
  created_at: string;
  summary: string;
};

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchMeetings() {
      setLoading(true);
      setError("");
      try {
        const res = await axios.get("http://localhost:8000/meetings", {
          headers: {
            "x-api-key": process.env.NEXT_PUBLIC_API_KEY
          }
        });
        setMeetings(res.data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || err.message || "Unknown error");
      }
      setLoading(false);
    }
    fetchMeetings();
  }, []);

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4">Meeting History</h1>
      {loading && <div>Loading...</div>}
      {error && <div className="text-red-500">{error}</div>}
      <ul className="space-y-4">
        {meetings.map(m => (
          <li key={m.id} className="border p-4 rounded shadow">
            <div className="font-semibold">File: {m.filename}</div>
            <div>Created At: {new Date(m.created_at).toLocaleString()}</div>
            <div className="text-gray-600 line-clamp-2">Summary: {m.summary}</div>
            {/* Button to view details */}
          </li>
        ))}
      </ul>
    </div>
  );
}
