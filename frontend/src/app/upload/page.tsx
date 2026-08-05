"use client";

import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowPathIcon,
  CloudArrowUpIcon,
  DocumentIcon,
  ExclamationCircleIcon,
} from "@heroicons/react/24/outline";

import { meetingService } from "@/lib/api";

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Upload failed";
}

function formatFileSize(bytes: number): string {
  if (bytes <= 0) return "0 Bytes";
  const units = ["Bytes", "KB", "MB", "GB"];
  const unitIndex = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** unitIndex;
  return `${value.toFixed(unitIndex === 0 ? 0 : 2)} ${units[unitIndex]}`;
}

function isAudioFile(file: File): boolean {
  return file.type.startsWith("audio/") || /\.(mp3|wav|m4a|aac|flac|ogg|webm)$/i.test(file.name);
}

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectFile = (candidate: File | undefined) => {
    if (!candidate) return;
    if (!isAudioFile(candidate)) {
      setFile(null);
      setError("Choose a supported audio file.");
      return;
    }
    setFile(candidate);
    setError(null);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragOver(false);
    selectFile(Array.from(event.dataTransfer.files).find(isAudioFile));
  };

  const handleFileSelect = (event: ChangeEvent<HTMLInputElement>) => {
    selectFile(event.target.files?.[0]);
  };

  const removeFile = () => {
    setFile(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError("Choose an audio file before uploading.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const result = await meetingService.analyzeMeeting(file);
      router.push(`/meeting/${result.meeting_id}`);
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Upload Meeting Recording</h1>
        <p className="mt-2 text-gray-600">
          The API stores the recording, queues transcription, and redirects you
          to the meeting page where processing status and structured outcomes are shown.
        </p>
      </header>

      <section className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        <form onSubmit={handleUpload} className="space-y-6">
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={(event) => {
              event.preventDefault();
              setDragOver(false);
            }}
            onDrop={handleDrop}
            className={`relative rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
              dragOver
                ? "border-blue-400 bg-blue-50"
                : "border-gray-300 hover:border-gray-400"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg,.webm"
              onChange={handleFileSelect}
              disabled={submitting}
              aria-label="Choose meeting audio"
              className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
            />
            <CloudArrowUpIcon className="mx-auto mb-4 h-12 w-12 rounded-full bg-gray-100 p-3 text-gray-600" />
            <p className="text-lg font-medium text-gray-900">
              Drop your audio file here, or click to browse
            </p>
            <p className="mt-1 text-sm text-gray-500">
              MP3, WAV, M4A, AAC, FLAC, OGG, and WebM are supported.
            </p>
          </div>

          {file ? (
            <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4">
              <div className="flex min-w-0 items-center gap-3">
                <DocumentIcon className="h-8 w-8 shrink-0 text-blue-600" />
                <div className="min-w-0">
                  <p className="truncate font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={removeFile}
                disabled={submitting}
                aria-label="Remove selected file"
                className="rounded px-3 py-1 text-gray-500 hover:bg-white hover:text-red-600 disabled:opacity-50"
              >
                Remove
              </button>
            </div>
          ) : null}

          {submitting ? (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
              <div className="flex items-center">
                <ArrowPathIcon className="mr-2 h-5 w-5 animate-spin" />
                Uploading and creating the processing job...
              </div>
            </div>
          ) : null}

          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex items-center text-sm text-red-700">
                <ExclamationCircleIcon className="mr-2 h-5 w-5 shrink-0 text-red-600" />
                {error}
              </div>
            </div>
          ) : null}

          <button
            type="submit"
            disabled={submitting || !file}
            className="flex w-full items-center justify-center rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <>
                <ArrowPathIcon className="mr-2 h-5 w-5 animate-spin" />
                Creating Job...
              </>
            ) : (
              <>
                <CloudArrowUpIcon className="mr-2 h-5 w-5" />
                Upload and Analyze
              </>
            )}
          </button>
        </form>

        <div className="mt-6 border-t border-gray-200 pt-6">
          <h2 className="mb-2 text-sm font-medium text-gray-900">For better results</h2>
          <ul className="space-y-1 text-sm text-gray-600">
            <li>• Use clear audio with limited background noise.</li>
            <li>• Keep speakers close enough to the microphone.</li>
            <li>• Use a multilingual Whisper model for non-English meetings.</li>
            <li>• Keep AI_PROVIDER set to local for private processing.</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
