"use client";

import React, { useState } from "react";
import api from "@/lib/api";
import { useRouter } from "next/navigation";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return setMsg("Please choose an audio file.");

    try {
      setLoading(true);
      setMsg(null);
      const form = new FormData();
      form.append("file", file);
      const res = await api.post("/analyze-meeting", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (res.status === 200) {
        router.push("/meetings");
      } else {
        setMsg(`Unexpected status: ${res.status}`);
      }
    } catch (err: any) {
      setMsg(err?.response?.data?.detail || err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: "40px auto" }}>
      <h1>Upload Meeting Audio</h1>
      <form onSubmit={handleUpload}>
        <input
          type="file"
          accept="audio/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !file} style={{ marginLeft: 12 }}>
          {loading ? "Uploading..." : "Upload & Analyze"}
        </button>
      </form>
      {msg && <p style={{ color: "crimson" }}>{msg}</p>}
      <p style={{ marginTop: 12, fontSize: 12, opacity: 0.7 }}>
        Tip: we’ll auto-redirect to “Meetings” after processing.
      </p>
    </main>
  );
}
