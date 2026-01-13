"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function Home() {
  // --- STATE ---
  const [file, setFile] = useState<File | null>(null);
  const [timeLimit, setTimeLimit] = useState(15);
  const [status, setStatus] = useState("idle"); // idle, uploading, processing, done, error
  const [summary, setSummary] = useState("");
  const [debugLog, setDebugLog] = useState("");

  // --- LOGIC ---
  const handleGenerate = async () => {
    if (!file) return;

    try {
      // 1. UPLOAD
      setStatus("uploading");
      setDebugLog("Uploading PDF to backend...");

      const formData = new FormData();
      formData.append("file", file);

      const uploadRes = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });

      if (!uploadRes.ok) throw new Error("Upload failed");

      const uploadData = await uploadRes.json();
      setDebugLog(`Upload complete. ID: ${uploadData.book_id}. Analyzing...`);

      // 2. PROCESS (Map-Reduce)
      setStatus("processing");
      setDebugLog(
        "Reading, chunking, and compressing content... (This takes 1-2 mins)"
      );

      const summarizeRes = await fetch(
        `http://127.0.0.1:8000/summarize/${uploadData.book_id}?time_limit=${timeLimit}`,
        { method: "POST" }
      );

      if (!summarizeRes.ok) throw new Error("Summarization failed");

      const summaryData = await summarizeRes.json();
      setSummary(summaryData.condensed_content);
      setStatus("done");
    } catch (error) {
      console.error(error);
      setStatus("error");
      setDebugLog("Something went wrong. Check console.");
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-8 md:p-12 font-sans text-gray-900">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
          {/* Header */}
          <div className="bg-gray-900 p-8 text-white">
            <h1 className="text-3xl font-bold tracking-tight">
              Adaptive Book Compressor
            </h1>
            <p className="opacity-80 mt-2 text-lg font-light">
              Turn 10 hours of reading into 15 minutes.
            </p>
          </div>

          <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-12">
            {/* LEFT: Controls */}
            <div className="space-y-8">
              {/* File Input */}
              <div className="p-6 border-2 border-dashed border-gray-200 rounded-xl hover:border-blue-500 transition-colors bg-gray-50">
                <label className="block font-semibold mb-4 text-gray-700">
                  1. Upload Book (PDF)
                </label>
                <input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
                />
              </div>

              {/* Slider */}
              <div className="p-6 border border-gray-100 rounded-xl shadow-sm bg-white">
                {/* Fixed: Removed 'block' to resolve conflict with 'flex' */}
                <label className="flex justify-between font-semibold mb-4 text-gray-700">
                  <span>2. Time Budget</span>
                  <span className="text-blue-600 font-bold">
                    {timeLimit} mins
                  </span>
                </label>
                <input
                  type="range"
                  min="2"
                  max="60"
                  value={timeLimit}
                  onChange={(e) => setTimeLimit(Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-2">
                  <span>Super Concise (2m)</span>
                  <span>Deep Dive (60m)</span>
                </div>
              </div>

              {/* Generate Button */}
              <button
                onClick={handleGenerate}
                disabled={
                  !file || status === "processing" || status === "uploading"
                }
                className={`w-full py-4 rounded-xl font-bold text-lg shadow-lg transition-all transform hover:-translate-y-1 ${
                  !file
                    ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                    : "bg-blue-600 hover:bg-blue-700 text-white"
                }`}
              >
                {status === "idle" && "Generate Summary"}
                {status === "uploading" && "Uploading PDF..."}
                {status === "processing" && "Thinking (AI is working)..."}
                {status === "done" && "Summarize Another"}
              </button>

              {/* Status Log */}
              {status !== "idle" && status !== "done" && (
                <div className="p-4 bg-blue-50 text-blue-800 rounded-lg text-sm font-mono animate-pulse border border-blue-100">
                  &gt; {debugLog}
                </div>
              )}
            </div>

            {/* RIGHT: Output */}
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 h-96 overflow-y-auto shadow-inner">
              {status === "done" ? (
                <article className="prose prose-blue max-w-none">
                  <ReactMarkdown>{summary}</ReactMarkdown>
                </article>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
                  <svg
                    className="w-16 h-16 opacity-20"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                    ></path>
                  </svg>
                  <p className="font-medium">
                    Your summary will be generated here.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
