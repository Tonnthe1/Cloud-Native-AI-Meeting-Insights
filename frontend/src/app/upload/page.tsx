"use client";

import React, { useState, useRef } from "react";
import { meetingService, getErrorMessage } from "@/lib/api";
import { AUDIO_EXTENSIONS, formatFileSize, isAudioFile } from "@/lib/format";
import { useRouter } from "next/navigation";
import {
  CloudArrowUpIcon,
  DocumentIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  ArrowPathIcon
} from "@heroicons/react/24/outline";

type Phase = "idle" | "uploading" | "done";

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const busy = phase !== "idle";

  const selectFile = (candidate: File | undefined) => {
    if (!candidate) return;
    if (!isAudioFile(candidate)) {
      setError(`"${candidate.name}" doesn't look like an audio file. Supported formats: ${AUDIO_EXTENSIONS.join(", ")}`);
      return;
    }
    setFile(candidate);
    setError(null);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (busy) return;
    selectFile(e.dataTransfer.files[0]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    selectFile(e.target.files?.[0]);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please choose an audio file.");
      return;
    }

    try {
      setPhase("uploading");
      setError(null);
      setUploadProgress(0);

      const result = await meetingService.analyzeMeeting(file, setUploadProgress);

      // Processing continues in the background; the meeting page shows
      // live status until the transcript and summary are ready.
      setPhase("done");
      router.push(`/meeting/${result.meeting_id}`);
    } catch (err) {
      setPhase("idle");
      setUploadProgress(0);
      setError(getErrorMessage(err, "Upload failed"));
    }
  };

  const removeFile = () => {
    setFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Upload Meeting Recording</h1>
        <p className="text-gray-600 mt-2">
          Upload your audio file to get AI-powered meeting insights including transcription, summary, and key points.
        </p>
      </div>

      {/* Upload Form */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 sm:p-8">
        <form onSubmit={handleUpload} className="space-y-6">
          {/* File Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-200 focus-within:ring-2 focus-within:ring-blue-500 ${
              dragOver
                ? "border-blue-400 bg-blue-50"
                : "border-gray-300 hover:border-gray-400"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              aria-label="Choose an audio file"
              accept={["audio/*", ...AUDIO_EXTENSIONS].join(",")}
              onChange={handleFileSelect}
              disabled={busy}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
            />

            <div className="space-y-4">
              <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-gray-100">
                <CloudArrowUpIcon className="h-6 w-6 text-gray-600" />
              </div>

              <div>
                <p className="text-lg font-medium text-gray-900">
                  Drop your audio file here, or click to browse
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Supports MP3, WAV, M4A, and other audio formats
                </p>
              </div>
            </div>
          </div>

          {/* Selected File Info */}
          {file && (
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center space-x-3 min-w-0">
                  <DocumentIcon className="h-8 w-8 shrink-0 text-blue-600" />
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 truncate">{file.name}</p>
                    <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  disabled={busy}
                  aria-label="Remove file"
                  className="text-xl leading-none text-gray-400 hover:text-red-500 disabled:opacity-50"
                >
                  ×
                </button>
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {busy && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-gray-600">
                <span>{phase === "done" ? "Upload complete" : "Uploading..."}</span>
                <span>{uploadProgress}%</span>
              </div>
              <div
                className="w-full bg-gray-200 rounded-full h-2"
                role="progressbar"
                aria-valuenow={uploadProgress}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-500 text-center flex items-center justify-center">
                {phase === "done" ? (
                  <>
                    <CheckCircleIcon className="h-4 w-4 mr-1 text-green-600" />
                    Queued for processing. Opening the meeting…
                  </>
                ) : uploadProgress < 100 ? (
                  "Sending your recording..."
                ) : (
                  "Saving and queueing your recording..."
                )}
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4" role="alert">
              <div className="flex items-start">
                <ExclamationCircleIcon className="h-5 w-5 shrink-0 text-red-600 mr-2" />
                <span className="text-sm text-red-700">{error}</span>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={busy || !file}
            className="w-full flex items-center justify-center px-4 py-3 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            {busy ? (
              <>
                <ArrowPathIcon className="animate-spin h-5 w-5 mr-2" />
                Uploading...
              </>
            ) : (
              <>
                <CloudArrowUpIcon className="h-5 w-5 mr-2" />
                Upload & Analyze
              </>
            )}
          </button>
        </form>

        {/* Tips */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Tips for best results:</h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Use clear, high-quality audio recordings</li>
            <li>• Ensure speakers are audible and not too far from the microphone</li>
            <li>• Minimize background noise when possible</li>
            <li>• Supported formats: MP3, WAV, M4A, and most common audio formats</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
