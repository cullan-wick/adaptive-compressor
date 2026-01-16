"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function Home() {
  // --- STATE ---
  const [file, setFile] = useState<File | null>(null);
  const [timeMinutes, setTimeMinutes] = useState(15);
  const [readingSpeed, setReadingSpeed] = useState(250); // WPM
  const [status, setStatus] = useState("idle");
  const [summary, setSummary] = useState("");
  const [debugLog, setDebugLog] = useState("");
  const [finalWordCount, setFinalWordCount] = useState<number | null>(null); // New State

  // --- LOGIC ---
  const handleGenerate = async () => {
    if (!file) return;

    try {
      // 1. UPLOAD
      setStatus("uploading");
      setDebugLog("Uploading PDF to backend...");
      setFinalWordCount(null); // Reset count on new run

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
        `http://127.0.0.1:8000/summarize/${uploadData.book_id}?time_limit=${timeMinutes}&wpm=${readingSpeed}`,
        { method: "POST" }
      );

      if (!summarizeRes.ok) throw new Error("Summarization failed");

      const summaryData = await summarizeRes.json();

      // Update State
      setSummary(summaryData.condensed_content);
      setFinalWordCount(summaryData.final_summary_words); // Capture exact count

      setStatus("done");
    } catch (error) {
      console.error(error);
      setStatus("error");
      setDebugLog("Something went wrong. Check console.");
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-8 md:p-12 font-sans text-gray-900">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* TOP CARD: CONTROLS */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
          {/* Header */}
          <div className="bg-gray-900 p-8 text-white text-center">
            <h1 className="text-3xl font-bold tracking-tight">
              Adaptive Book Compressor
            </h1>
            <p className="opacity-80 mt-2 text-lg font-light">
              Turn 10 hours of reading into {timeMinutes} minutes.
            </p>
          </div>

          {/* Controls Container */}
          <div className="p-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
              {/* Input 1: File */}
              <div className="p-6 border-2 border-dashed border-gray-200 rounded-xl hover:border-blue-500 transition-colors bg-gray-50 flex flex-col justify-center">
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

              {/* Input 2: Time & Reading Speed */}
              <div className="p-6 border border-gray-100 rounded-xl shadow-sm bg-white flex flex-col justify-center space-y-6">
                {/* Time Input */}
                <div>
                  <label className="flex justify-between font-semibold mb-3 text-gray-700">
                    <span>2. Available Time</span>
                    <span className="text-blue-600 font-bold">
                      {timeMinutes} mins
                    </span>
                  </label>
                  <input
                    type="number"
                    min="2"
                    max="120"
                    value={timeMinutes}
                    onChange={(e) => setTimeMinutes(Number(e.target.value))}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none text-lg font-semibold text-gray-700 transition-all"
                    placeholder="Minutes"
                  />
                </div>

                {/* Reading Speed Slider */}
                <div>
                  <label className="flex justify-between font-semibold mb-3 text-gray-700">
                    <span>Reading Speed</span>
                    <span className="text-blue-600 font-bold">
                      {readingSpeed} WPM
                    </span>
                  </label>
                  <input
                    type="range"
                    min="100"
                    max="400"
                    step="10"
                    value={readingSpeed}
                    onChange={(e) => setReadingSpeed(Number(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-2">
                    <span>Slow (100)</span>
                    <span>Average (250)</span>
                    <span>Fast (400)</span>
                  </div>
                </div>

                {/* DYNAMIC ESTIMATE DISPLAY */}
                <div className="pt-4 border-t border-gray-100 flex justify-between items-center">
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-wide">
                    Target Length
                  </span>
                  <span className="text-xl font-bold text-gray-800">
                    ~{(timeMinutes * readingSpeed).toLocaleString()} words
                  </span>
                </div>
              </div>
            </div>

            {/* Action Area */}
            <div className="max-w-2xl mx-auto flex flex-col gap-4">
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
                <div className="text-center p-3 bg-blue-50 text-blue-800 rounded-lg text-sm font-mono animate-pulse border border-blue-100">
                  &gt; {debugLog}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* BOTTOM CARD: SUMMARY OUTPUT */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8 md:p-12 min-h-125">
          {status === "done" ? (
            <div className="space-y-6">
              {/* ACTUAL WORD COUNT BADGE */}
              <div className="flex items-center justify-between border-b border-gray-100 pb-4">
                <span className="text-sm font-bold text-gray-400 uppercase tracking-wider">
                  Generated Summary
                </span>
                <div className="flex items-center gap-2 bg-green-50 px-4 py-1.5 rounded-full border border-green-100">
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                  <span className="text-sm font-bold text-green-700">
                    {finalWordCount?.toLocaleString()} words
                  </span>
                </div>
              </div>

              <article className="prose prose-lg prose-blue max-w-none">
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => (
                      <p
                        className="mb-6 leading-relaxed text-gray-800"
                        {...props}
                      />
                    ),
                    h1: ({ node, ...props }) => (
                      <h1
                        className="text-3xl font-bold mt-8 mb-4 text-gray-900"
                        {...props}
                      />
                    ),
                    h2: ({ node, ...props }) => (
                      <h2
                        className="text-2xl font-bold mt-8 mb-4 text-gray-900 border-b pb-2"
                        {...props}
                      />
                    ),
                    h3: ({ node, ...props }) => (
                      <h3
                        className="text-xl font-bold mt-6 mb-3 text-blue-700"
                        {...props}
                      />
                    ),
                    ul: ({ node, ...props }) => (
                      <ul
                        className="list-disc pl-5 mb-6 space-y-2"
                        {...props}
                      />
                    ),
                    li: ({ node, ...props }) => (
                      <li className="pl-1" {...props} />
                    ),
                  }}
                >
                  {summary}
                </ReactMarkdown>
              </article>
            </div>
          ) : (
            // PLACEHOLDER STATE
            <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-6 min-h-75">
              <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center">
                <svg
                  className="w-12 h-12 opacity-20 text-gray-600"
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
              </div>
              <p className="font-medium text-lg">
                Your summary will appear here
              </p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
