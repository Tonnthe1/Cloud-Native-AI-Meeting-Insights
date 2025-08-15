"use client";

import React, { useState, useRef } from "react";
import { meetingService } from "@/lib/api";
import { useRouter } from "next/navigation";
import {
  CloudArrowUpIcon,
  DocumentIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  ArrowPathIcon
} from "@heroicons/react/24/outline";

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

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
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    const audioFile = droppedFiles.find(file => file.type.startsWith('audio/'));
    
    if (audioFile) {
      setFile(audioFile);
      setError(null);
    } else {
      setError("Please drop an audio file");
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please choose an audio file.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setUploadProgress(0);
      
      // Simulate upload progress (since we can't get real progress from the API easily)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);
      
      const result = await meetingService.analyzeMeeting(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      // Brief delay to show completion
      setTimeout(() => {
        router.push("/");
      }, 1000);
      
    } catch (err: any) {
      setUploadProgress(0);
      setError(err?.response?.data?.detail || err.message || "Upload failed");
    } finally {
      setLoading(false);
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
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <form onSubmit={handleUpload} className="space-y-6">
          {/* File Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-200 ${
              dragOver
                ? "border-blue-400 bg-blue-50"
                : "border-gray-300 hover:border-gray-400"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              onChange={handleFileSelect}
              disabled={loading}
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
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <DocumentIcon className="h-8 w-8 text-blue-600" />
                  <div>
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  disabled={loading}
                  className="text-gray-400 hover:text-red-500 disabled:opacity-50"
                >
                  ×
                </button>
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {loading && uploadProgress > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Processing...</span>
                <span className="text-gray-600">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-500 text-center">
                {uploadProgress < 30 && "Uploading file..."}
                {uploadProgress >= 30 && uploadProgress < 60 && "Transcribing audio..."}
                {uploadProgress >= 60 && uploadProgress < 90 && "Generating summary..."}
                {uploadProgress >= 90 && uploadProgress < 100 && "Finishing up..."}
                {uploadProgress === 100 && "Complete! Redirecting..."}
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <ExclamationCircleIcon className="h-5 w-5 text-red-600 mr-2" />
                <span className="text-sm text-red-700">{error}</span>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading || !file}
            className="w-full flex items-center justify-center px-4 py-3 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            {loading ? (
              <>
                <ArrowPathIcon className="animate-spin h-5 w-5 mr-2" />
                Processing...
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