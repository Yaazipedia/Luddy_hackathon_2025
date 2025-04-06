"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Mic,
  Upload,
  Image as ImageIcon,
  Layers,
  AlignLeft,
  CheckSquare,
  AlertTriangle,
  ChevronDown,
  Users,
  Plus,
  Send,
  Trash,
  Globe,
} from "lucide-react";

export default function MeetSmartDashboard() {
  const [activeTab, setActiveTab] = useState("live");
  const [expandedSection, setExpandedSection] = useState("summary");
  const [transcript, setTranscript] = useState([]);
  const [actions, setActions] = useState([]);
  const [summary, setSummary] = useState({});
  const [summarySentences, setSummarySentences] = useState([]);
  const [visualizations, setVisualizations] = useState({});
  const [fetchedImages, setFetchedImages] = useState({});
  const [selectedEmails, setSelectedEmails] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [translationFile, setTranslationFile] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState("en");
  const [translatedSummary, setTranslatedSummary] = useState([]);

  const [newParticipant, setNewParticipant] = useState({
    name: "",
    email: "",
    role: "",
  });
  const [participants, setParticipants] = useState([]);

  const handleDeleteParticipants = () => {
    setParticipants((prev) =>
      prev.filter((p) => !selectedEmails.includes(p.email))
    );
    setSelectedEmails([]); // clear selection after deletion
  };
  const handleCheckboxChange = (email) => {
    setSelectedEmails((prev) =>
      prev.includes(email) ? prev.filter((e) => e !== email) : [...prev, email]
    );
  };

  const handleSendEmails = async () => {
    try {
      const res = await fetch("http://10.20.31.189:8000/send-latest-report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ recipients: selectedEmails }),
      });

      if (!res.ok) throw new Error("Failed to send emails");
      alert("Emails sent successfully!");
    } catch (err) {
      console.error(err);
      alert("Something went wrong while sending emails.");
    }
  };

  const fileInputRef = useRef(null);

  const handleUploadClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setTranscript([`Uploading ${file.name}…`]);
    const formData = new FormData();
    formData.append("audio_file", file);

    try {
      const res = await fetch("http://10.20.31.189:8000/process-audio-file", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      const data = await res.json();

      const fetchFile = async (path) => {
        const res = await fetch("http://10.20.31.189:8000/read-file", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file_path: path }),
        });
        if (!res.ok) throw new Error(`Server responded ${res.status}`);
        return res.json();
      };

      const transcriptRes = await fetchFile(data.transcript_path);
      setTranscript(
        transcriptRes.content
          .split("\n")
          .map((l) => l.trim())
          .filter((l) => l)
      );

      const actionRes = await fetchFile(data.action_items_path);
      setActions(
        actionRes.content.map((item) => ({
          task: item.action,
          owner: item.assigned_to || "Unassigned",
        }))
      );

      const sentimentRes = await fetchFile(data.sentiment_path);
      setSummary(sentimentRes.content);

      if (
        sentimentRes.content?.Speaker_1?.detailed_analysis ||
        sentimentRes.content?.Speaker_2?.detailed_analysis
      ) {
        const speakers = Object.values(sentimentRes.content);
        const combinedSummary = speakers
          .map((s) => s.detailed_analysis.map((u) => u.text))
          .flat();

        setSummarySentences(combinedSummary);
      }

      setVisualizations(data.visualizations || {});
    } catch (err) {
      setTranscript([`Upload failed: ${err.message || "Unknown error"}`]);
    }
  };

  useEffect(() => {
    const fetchAllImages = async () => {
      const entries = Object.entries(visualizations);
      const results = {};

      for (const [label, path] of entries) {
        try {
          const res = await fetch("http://10.20.31.189:8000/read-file", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ file_path: path }),
          });

          if (res.ok) {
            const blob = await res.blob();
            const objectURL = URL.createObjectURL(blob);
            results[label] = objectURL;
          }
        } catch (err) {
          console.error(`Failed to load ${label}:`, err);
        }
      }

      setFetchedImages(results);
    };

    if (Object.keys(visualizations).length > 0) {
      fetchAllImages();
    }
  }, [visualizations]);

  const getSpeakerName = (speakerKey, idx) => {
    return participants[idx]?.name || speakerKey;
  };

  return (
    <div className="flex h-screen bg-gray-100 text-gray-800">
      {/* Sidebar */}
      <div className="w-16 bg-indigo-800 flex flex-col items-center py-6 text-white">
        <div className="mb-10">
          <Layers size={24} />
        </div>
        <div
          className={`my-4 p-2 rounded-lg ${
            activeTab === "live" ? "bg-indigo-700" : ""
          }`}
          onClick={() => setActiveTab("live")}
        >
          <Mic size={20} />
        </div>
        <div
          className={`my-4 p-2 rounded-lg ${
            activeTab === "participants" ? "bg-indigo-700" : ""
          }`}
          onClick={() => setActiveTab("participants")}
        >
          <Users size={20} />
        </div>
        <div
          className={`my-4 p-2 rounded-lg ${
            activeTab === "visualizations" ? "bg-indigo-700" : ""
          }`}
          onClick={() => setActiveTab("visualizations")}
        >
          <ImageIcon size={20} />
        </div>
        <div
          className={`my-4 p-2 rounded-lg ${
            activeTab === "translate" ? "bg-indigo-700" : ""
          }`}
          onClick={() => setActiveTab("translate")}
        >
          <Globe size={20} />
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {activeTab === "live" && (
          <>
            <header className="bg-white border-b border-gray-200 p-4 flex justify-between items-center">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold">MeetSmart</h1>
                <button
                  onClick={handleUploadClick}
                  className="ml-6 bg-indigo-600 text-white px-4 py-2 rounded-md flex items-center"
                >
                  <Upload size={16} className="mr-2" /> Upload
                </button>
                <input
                  type="file"
                  accept=".mp3,.mp4,.wav"
                  ref={fileInputRef}
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
            </header>
            <div className="flex-1 flex overflow-hidden">
              <div className="w-1/2 bg-white overflow-y-auto p-4 border-r border-gray-200">
                <h2 className="font-semibold mb-4">Transcript</h2>
                {transcript.map((line, idx) => (
                  <p key={idx} className="text-sm mb-2 text-gray-700">
                    {line}
                  </p>
                ))}
              </div>

              <div className="w-1/2 bg-gray-50 overflow-y-auto p-4 space-y-6">
                <div>
                  <div
                    className="flex justify-between items-center cursor-pointer"
                    onClick={() =>
                      setExpandedSection(
                        expandedSection === "summary" ? "" : "summary"
                      )
                    }
                  >
                    <div className="flex items-center">
                      <AlignLeft size={16} className="mr-2 text-indigo-600" />
                      <h3 className="font-semibold">Summary</h3>
                    </div>
                    <ChevronDown
                      size={16}
                      className={`transition-transform ${
                        expandedSection === "summary" ? "rotate-180" : ""
                      }`}
                    />
                  </div>
                  {expandedSection === "summary" && (
                    <div className="mt-2 space-y-2 text-sm text-gray-800">
                      {summarySentences.map((s, i) => (
                        <p key={i}>{s}.</p>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <div
                    className="flex justify-between items-center cursor-pointer"
                    onClick={() =>
                      setExpandedSection(
                        expandedSection === "actions" ? "" : "actions"
                      )
                    }
                  >
                    <div className="flex items-center">
                      <CheckSquare size={16} className="mr-2 text-indigo-600" />
                      <h3 className="font-semibold">Action Items</h3>
                    </div>
                    <ChevronDown
                      size={16}
                      className={`transition-transform ${
                        expandedSection === "actions" ? "rotate-180" : ""
                      }`}
                    />
                  </div>
                  {expandedSection === "actions" && (
                    <div className="mt-2 space-y-2 text-sm">
                      {actions.map((item, idx) => (
                        <div key={idx} className="bg-white p-2 rounded shadow">
                          <p>{item.task}</p>
                          <p className="text-xs text-gray-500">
                            Owner: {item.owner}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex items-center mb-2">
                    <AlertTriangle size={16} className="mr-2 text-indigo-600" />
                    <h3 className="font-semibold">Sentiment Analysis</h3>
                  </div>

                  {Object.keys(summary).length > 0 && (
                    <>
                      <div className="mb-4">
                        <p className="text-sm font-medium mb-1">
                          Overall Meeting Tone
                        </p>
                        <div className="relative w-full h-3 rounded bg-gray-200 overflow-hidden">
                          <div
                            className="absolute top-0 left-0 h-full rounded transition-all"
                            style={{
                              width: `${
                                (Object.values(summary).reduce(
                                  (acc, s) => acc + s.average_compound,
                                  0
                                ) /
                                  Object.keys(summary).length) *
                                100
                              }%`,
                              backgroundColor:
                                Object.values(summary).reduce(
                                  (acc, s) => acc + s.average_compound,
                                  0
                                ) /
                                  Object.keys(summary).length >
                                0.7
                                  ? "#22c55e"
                                  : Object.values(summary).reduce(
                                      (acc, s) => acc + s.average_compound,
                                      0
                                    ) /
                                      Object.keys(summary).length >
                                    0.4
                                  ? "#eab308"
                                  : "#ef4444",
                            }}
                          />
                        </div>
                        <p className="text-right text-sm font-semibold mt-1 text-gray-700">
                          {Math.round(
                            (Object.values(summary).reduce(
                              (acc, s) => acc + s.average_compound,
                              0
                            ) /
                              Object.keys(summary).length) *
                              100
                          )}
                          %
                        </p>
                      </div>

                      <p className="text-sm font-medium mb-1">By Participant</p>
                      <div className="space-y-3">
                        {Object.entries(summary).map(
                          ([speakerKey, data], idx) => {
                            const name = getSpeakerName(speakerKey, idx);
                            const percent = Math.round(
                              data.average_compound * 100
                            );
                            const color =
                              percent > 70
                                ? "#22c55e"
                                : percent > 40
                                ? "#eab308"
                                : "#ef4444";

                            return (
                              <div key={speakerKey}>
                                <div className="flex justify-between text-sm font-medium mb-1">
                                  <span>{name}</span>
                                  <span style={{ color }}>{percent}%</span>
                                </div>
                                <div className="relative w-full h-3 rounded bg-gray-200 overflow-hidden">
                                  <div
                                    className="absolute top-0 left-0 h-full rounded"
                                    style={{
                                      width: `${percent}%`,
                                      backgroundColor: color,
                                    }}
                                  />
                                </div>
                              </div>
                            );
                          }
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === "participants" && (
          <div className="flex-1 overflow-y-auto p-6">
            {/* Top Bar */}
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold flex items-center">
                Participants
                <Plus
                  size={20}
                  className="ml-2 text-indigo-600 cursor-pointer"
                  onClick={() => setShowModal(true)}
                />
              </h2>

              {selectedEmails.length > 0 && (
                <div className="flex gap-2">
                  <button
                    onClick={handleSendEmails}
                    className="flex items-center bg-indigo-600 text-white px-4 py-2 rounded-md shadow hover:bg-indigo-700 transition"
                  >
                    <Send size={16} className="mr-2" />
                    Send Email
                  </button>
                  <button
                    onClick={handleDeleteParticipants}
                    className="flex items-center bg-red-600 text-white px-4 py-2 rounded-md shadow hover:bg-red-700 transition"
                  >
                    <Trash size={16} className="mr-2" />
                    <span className="ml-2">Delete Selected</span>
                  </button>
                </div>
              )}
            </div>

            {/* Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {participants.map((p, i) => (
                <div
                  key={i}
                  className="bg-white p-4 rounded-lg shadow border flex items-start gap-4"
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selectedEmails.includes(p.email)}
                    onChange={() => handleCheckboxChange(p.email)}
                  />
                  <div className="flex flex-col">
                    <p className="text-base font-medium">{p.name}</p>
                    <p className="text-sm text-gray-600">{p.email}</p>
                    <p className="text-sm text-gray-500">{p.role}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "visualizations" && (
          <div className="flex-1 overflow-y-auto p-6">
            <h2 className="text-xl font-semibold mb-4">Visualizations</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-6">
              {Object.entries(fetchedImages).map(([label, url], idx) => (
                <div key={idx} className="bg-white rounded shadow p-3">
                  <p className="text-sm font-medium mb-2 capitalize">
                    {label.replace(/_/g, " ")}
                  </p>
                  <img
                    src={url}
                    alt={label}
                    className="w-full h-auto rounded"
                  />
                </div>
              ))}
            </div>
          </div>
        )}
        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-[4px]">
            <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-md">
              <h3 className="text-lg font-semibold mb-4">Add Participant</h3>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  setParticipants((prev) => [...prev, newParticipant]);
                  setNewParticipant({ name: "", email: "", role: "" });
                  setShowModal(false);
                }}
                className="space-y-4"
              >
                <input
                  type="text"
                  placeholder="Name"
                  value={newParticipant.name}
                  onChange={(e) =>
                    setNewParticipant({
                      ...newParticipant,
                      name: e.target.value,
                    })
                  }
                  className="w-full p-2 border border-gray-300 rounded"
                  required
                />
                <input
                  type="email"
                  placeholder="Email"
                  value={newParticipant.email}
                  onChange={(e) =>
                    setNewParticipant({
                      ...newParticipant,
                      email: e.target.value,
                    })
                  }
                  className="w-full p-2 border border-gray-300 rounded"
                  required
                />
                <input
                  type="text"
                  placeholder="Role"
                  value={newParticipant.role}
                  onChange={(e) =>
                    setNewParticipant({
                      ...newParticipant,
                      role: e.target.value,
                    })
                  }
                  className="w-full p-2 border border-gray-300 rounded"
                />
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 rounded bg-gray-200 hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700"
                  >
                    Add
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
        {activeTab === "translate" && (
          <>
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <header className="bg-white border-b border-gray-200 p-4 flex justify-between items-center">
                <h2 className="text-xl font-semibold">Translation</h2>

                {/* Language Dropdown */}
                <div>
                  <label className="block mb-1 font-medium text-sm">
                    Select Language
                  </label>
                  <select
                    value={selectedLanguage}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                    className="border p-2 rounded text-sm w-64"
                  >
                    <option value="en">English</option>
                    <option value="fr">French</option>
                    <option value="es">Spanish</option>
                    <option value="de">German</option>
                    <option value="ja">Japanese</option>
                    <option value="zh-CN">Chinese</option>
                    <option value="hi">Hindi</option>
                  </select>
                </div>

                {/* Upload Button */}
                <div>
                  <button
                    onClick={() =>
                      document.getElementById("translation-file-input").click()
                    }
                    className="bg-indigo-600 text-white px-4 py-2 rounded-md flex items-center hover:bg-indigo-700"
                  >
                    <Upload size={16} className="mr-2" />
                    Upload
                  </button>
                  <input
                    id="translation-file-input"
                    type="file"
                    accept=".mp3,.mp4,.wav,.txt"
                    className="hidden"
                    onChange={(e) =>
                      setTranslationFile(e.target.files?.[0] || null)
                    }
                  />
                </div>
              </header>

              {/* Translated Summary Output */}
              {translatedSummary.length > 0 && (
                <div className="mt-6 space-y-2">
                  <h3 className="font-semibold">Translated Summary:</h3>
                  {translatedSummary.map((s, idx) => (
                    <p key={idx} className="text-sm text-gray-700">
                      {s}.
                    </p>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
