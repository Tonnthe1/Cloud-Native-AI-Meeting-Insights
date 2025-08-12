"use client";

import React, { useEffect, useState } from "react";
import api from "@/lib/api";

type Meeting = {
  id: number;
  filename: string;
  transcript?: string | null;
  summary?: string | null;
  created_at: string;
};

export default function MeetingsPage() {
  const [items, setItems] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function fetchMeetings() {
    try {
      setLoading(true);
      setErr(null);
      const res = await api.get<Meeting[]>("/meetings");
      setItems(res.data);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e.message || "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchMeetings();
  }, []);

  return (
    <main style={{ maxWidth: 900, margin: "40px auto" }}>
      <h1>Meetings</h1>
      <button onClick={fetchMeetings} disabled={loading} style={{ marginBottom: 12 }}>
        {loading ? "Refreshing..." : "Refresh"}
      </button>
      {err && <p style={{ color: "crimson" }}>{err}</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {items.map((m) => (
          <li key={m.id} style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8, marginBottom: 12 }}>
            <div style={{ fontWeight: 600 }}>{m.filename}</div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>Created: {new Date(m.created_at).toLocaleString()}</div>
            <div style={{ marginTop: 8 }}>
              <strong>Summary:</strong>
              <div style={{ whiteSpace: "pre-wrap" }}>{m.summary || "(not available)"}</div>
            </div>
          </li>
        ))}
      </ul>
      {items.length === 0 && !loading && <p>No meetings yet. Try uploading one!</p>}
    </main>
  );
}
