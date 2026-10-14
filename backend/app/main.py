import os
import io
import zipfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from app.config import settings
from app.db.database import engine, Base
from app.routers import meetings, telephony, actions, mcp, settings as settings_router

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gemini AI Meeting Minutes & Telephony Gateway",
    description="Captures Google Meet / Teams & IVR conversations, generates MoM & actions with Gemini, and dispatches recap packages.",
    version="1.0.0"
)

# Enable CORS for Chrome Extension and external origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(meetings.router)
app.include_router(telephony.router)
app.include_router(actions.router)
app.include_router(mcp.router)
app.include_router(settings_router.router)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gemini AI Meeting Intelligence & MoM Hub</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">
  <!-- Navbar -->
  <nav class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-sky-500/20">
          <i class="fa-solid fa-brain text-xl"></i>
        </div>
        <div>
          <h1 class="font-bold text-lg leading-tight bg-gradient-to-r from-sky-400 to-indigo-300 bg-clip-text text-transparent">Gemini Meeting Agent</h1>
          <p class="text-xs text-slate-400">Autonomous Minutes, Actions & IVR Platform</p>
        </div>
      </div>
      <div class="flex items-center gap-4">
        <a href="/docs" target="_blank" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition flex items-center gap-2">
          <i class="fa-solid fa-code"></i> API Docs
        </a>
        <button onclick="document.getElementById('uploadModal').classList.remove('hidden')" class="text-xs bg-sky-600 hover:bg-sky-500 text-white font-semibold px-4 py-1.5 rounded-lg transition flex items-center gap-2 shadow-lg shadow-sky-600/30">
          <i class="fa-solid fa-cloud-arrow-up"></i> Upload Audio
        </button>
      </div>
    </div>
  </nav>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Top Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
      <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
        <p class="text-xs text-slate-400 font-medium">Total Meetings</p>
        <p id="totalMeetingsCount" class="text-2xl font-bold text-slate-100 mt-1">0</p>
      </div>
      <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
        <p class="text-xs text-slate-400 font-medium">Action Items Tracked</p>
        <p id="totalActionsCount" class="text-2xl font-bold text-sky-400 mt-1">0</p>
      </div>
      <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
        <p class="text-xs text-slate-400 font-medium">Gemini Intelligence</p>
        <p class="text-2xl font-bold text-emerald-400 mt-1">Active</p>
      </div>
      <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
        <p class="text-xs text-slate-400 font-medium">IVR Gateway Status</p>
        <p class="text-2xl font-bold text-indigo-400 mt-1">Listening</p>
      </div>
    </div>

    <!-- Layout: Meetings List & Details View -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <!-- Meetings Sidebar List -->
      <div class="lg:col-span-4 space-y-3">
        <div class="flex items-center justify-between pb-2">
          <h2 class="font-semibold text-sm uppercase tracking-wider text-slate-400">Recorded Meetings</h2>
          <button onclick="loadMeetings()" class="text-xs text-sky-400 hover:underline"><i class="fa-solid fa-rotate-right"></i> Refresh</button>
        </div>
        <div id="meetingsList" class="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
          <!-- Dynamically populated meetings -->
        </div>
      </div>

      <!-- Detail View / MoM Inspector -->
      <div class="lg:col-span-8">
        <div id="emptyState" class="bg-slate-800/40 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 flex flex-col items-center justify-center min-h-[450px]">
          <i class="fa-solid fa-microphone-lines text-5xl text-slate-600 mb-4"></i>
          <h3 class="text-lg font-semibold text-slate-200">Select a meeting to view Minutes & Actions</h3>
          <p class="text-sm text-slate-400 max-w-sm mt-1">Record a session via the Chrome Extension or upload an audio file to view Gemini's structured output.</p>
        </div>

        <div id="meetingDetail" class="hidden bg-slate-800/80 border border-slate-700 rounded-2xl p-6 space-y-6 shadow-xl">
          <!-- Detail Header -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-700 gap-4">
            <div>
              <div class="flex items-center gap-2">
                <span id="detailSourceBadge" class="text-xs px-2.5 py-0.5 rounded-full font-medium bg-sky-900/60 text-sky-300 border border-sky-700">Web Extension</span>
                <span id="detailSentimentBadge" class="text-xs px-2.5 py-0.5 rounded-full font-medium bg-emerald-900/60 text-emerald-300 border border-emerald-700">Productive</span>
              </div>
              <h2 id="detailTitle" class="text-xl font-bold text-white mt-1.5">Meeting Title</h2>
              <p id="detailMeta" class="text-xs text-slate-400 mt-0.5"></p>
            </div>
            <div class="flex items-center gap-2">
              <a id="downloadPdfBtn" href="#" target="_blank" class="text-xs bg-slate-700 hover:bg-slate-600 text-white font-medium px-3.5 py-2 rounded-lg transition flex items-center gap-2 border border-slate-600">
                <i class="fa-solid fa-file-pdf text-red-400"></i> Download PDF
              </a>
              <button id="resendEmailBtn" onclick="resendCurrentEmail()" class="text-xs bg-sky-600 hover:bg-sky-500 text-white font-medium px-3.5 py-2 rounded-lg transition flex items-center gap-2 shadow-md shadow-sky-600/30">
                <i class="fa-solid fa-paper-plane"></i> Send Recap Email
              </button>
            </div>
          </div>

          <!-- Executive Summary -->
          <div>
            <h3 class="text-xs font-bold uppercase tracking-wider text-sky-400 mb-2">Executive Summary</h3>
            <p id="detailExecutiveSummary" class="text-sm text-slate-300 leading-relaxed bg-slate-900/60 p-4 rounded-xl border border-slate-800"></p>
          </div>

          <!-- Key Decisions -->
          <div id="decisionsContainer">
            <h3 class="text-xs font-bold uppercase tracking-wider text-sky-400 mb-2">Key Decisions Made</h3>
            <ul id="detailDecisionsList" class="space-y-1.5 text-sm text-slate-300 pl-4 list-disc"></ul>
          </div>

          <!-- Action Items Table -->
          <div>
            <h3 class="text-xs font-bold uppercase tracking-wider text-sky-400 mb-2">Assigned Action Items</h3>
            <div class="overflow-x-auto border border-slate-700/80 rounded-xl">
              <table class="w-full text-left text-xs">
                <thead class="bg-slate-900/90 text-slate-400 uppercase font-semibold border-b border-slate-700">
                  <tr>
                    <th class="px-4 py-3">Task</th>
                    <th class="px-4 py-3">Assignee</th>
                    <th class="px-4 py-3">Deadline</th>
                    <th class="px-4 py-3">Priority</th>
                    <th class="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody id="detailActionsTable" class="divide-y divide-slate-700/60 bg-slate-900/40"></tbody>
              </table>
            </div>
          </div>

          <!-- Topics Discussion -->
          <div>
            <h3 class="text-xs font-bold uppercase tracking-wider text-sky-400 mb-2">Agenda Topics & Notes</h3>
            <div id="detailTopicsList" class="space-y-3"></div>
          </div>

          <!-- Full Verbatim Speaker Transcript -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-xs font-bold uppercase tracking-wider text-sky-400 flex items-center gap-2">
                <i class="fa-solid fa-microphone-lines"></i> Full Verbatim Speaker Transcript
              </h3>
              <div class="flex items-center gap-2">
                <input type="text" id="transcriptSearchInput" oninput="filterTranscript()" placeholder="Search speech..." class="text-[11px] bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-slate-200 outline-none focus:border-sky-500">
                <button onclick="copyFullTranscript()" id="copyTranscriptBtn" class="text-[11px] bg-slate-700 hover:bg-slate-600 text-slate-300 px-2.5 py-1 rounded transition flex items-center gap-1 border border-slate-600">
                  <i class="fa-solid fa-copy"></i> Copy Text
                </button>
              </div>
            </div>
            <div id="detailTranscriptList" class="space-y-2.5 bg-slate-900/60 border border-slate-800 p-4 rounded-xl max-h-96 overflow-y-auto font-sans">
              <!-- Dynamically populated speech turns -->
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>

  <!-- Upload Modal -->
  <div id="uploadModal" class="hidden fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-slate-800 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-700">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <i class="fa-solid fa-cloud-arrow-up text-sky-400"></i> Process Audio Recording
        </h3>
        <button onclick="document.getElementById('uploadModal').classList.add('hidden')" class="text-slate-400 hover:text-white">&times;</button>
      </div>

      <form id="uploadForm" onsubmit="handleAudioUpload(event)" class="space-y-4 text-xs">
        <div>
          <label class="block font-medium text-slate-300 mb-1">Meeting Title</label>
          <input type="text" id="uploadTitle" required value="Product Architecture Sync" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white outline-none focus:border-sky-500">
        </div>
        <div>
          <label class="block font-medium text-slate-300 mb-1">Participants (comma separated)</label>
          <input type="text" id="uploadParticipants" placeholder="Alex (alex@example.com), Jordan (jordan@example.com)" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white outline-none focus:border-sky-500">
        </div>
        <div>
          <label class="block font-medium text-slate-300 mb-1">Audio File (.wav, .webm, .mp3, .ogg)</label>
          <input type="file" id="uploadAudioFile" required accept="audio/*" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-300">
        </div>
        <div class="flex items-center gap-2">
          <input type="checkbox" id="uploadAutoEmail" checked class="rounded bg-slate-900 border-slate-700 text-sky-600 focus:ring-0">
          <label for="uploadAutoEmail" class="text-slate-300">Automatically dispatch recap email to participants</label>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" onclick="document.getElementById('uploadModal').classList.add('hidden')" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white">Cancel</button>
          <button type="submit" id="uploadSubmitBtn" class="px-4 py-2 bg-sky-600 hover:bg-sky-500 rounded-lg text-white font-semibold flex items-center gap-2">
            <span>Process with Gemini</span>
          </button>
        </div>
      </form>
    </div>
  </div>

  <script>
    let currentSelectedMeetingId = null;

    async function loadMeetings() {
      try {
        const res = await fetch('/api/v1/meetings');
        const data = await res.json();
        document.getElementById('totalMeetingsCount').textContent = data.length;

        const listEl = document.getElementById('meetingsList');
        listEl.innerHTML = '';

        if (data.length === 0) {
          listEl.innerHTML = '<div class="text-xs text-slate-500 p-4 bg-slate-800/20 rounded-xl text-center">No meetings recorded yet.</div>';
          return;
        }

        data.forEach(m => {
          const item = document.createElement('div');
          item.className = `p-3.5 rounded-xl border cursor-pointer transition ${currentSelectedMeetingId === m.id ? 'bg-sky-950/40 border-sky-600' : 'bg-slate-800/40 border-slate-800 hover:bg-slate-800/80 hover:border-slate-700'}`;
          item.onclick = () => selectMeeting(m.id);
          item.innerHTML = `
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-semibold uppercase tracking-wider text-slate-400">${m.source.replace('_', ' ')}</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full ${m.status === 'completed' ? 'bg-emerald-900/50 text-emerald-300' : 'bg-amber-900/50 text-amber-300'}">${m.status}</span>
            </div>
            <h4 class="font-semibold text-sm text-slate-100 mt-1 truncate">${m.title}</h4>
            <div class="flex items-center justify-between text-xs text-slate-400 mt-2">
              <span><i class="fa-solid fa-users text-slate-500 mr-1"></i> ${m.participants_count}</span>
              <span><i class="fa-solid fa-list-check text-slate-500 mr-1"></i> ${m.action_items_count} items</span>
              <span>${m.duration_seconds ? m.duration_seconds + 's' : ''}</span>
            </div>
          `;
          listEl.appendChild(item);
        });

        // Update actions count
        const actionsRes = await fetch('/api/v1/actions');
        const actionsData = await actionsRes.json();
        document.getElementById('totalActionsCount').textContent = actionsData.length;

        // Auto-select latest meeting if none currently selected
        if (!currentSelectedMeetingId && data.length > 0) {
          selectMeeting(data[0].id);
        }

      } catch (err) {
        console.error('Failed to load meetings:', err);
      }
    }

    async function selectMeeting(id) {
      currentSelectedMeetingId = id;
      loadMeetings(); // highlight selected
      const res = await fetch(`/api/v1/meetings/${id}`);
      const m = await res.json();

      document.getElementById('emptyState').classList.add('hidden');
      document.getElementById('meetingDetail').classList.remove('hidden');

      document.getElementById('detailTitle').textContent = m.title;
      document.getElementById('detailSourceBadge').textContent = m.source.replace('_', ' ');
      document.getElementById('detailMeta').textContent = `Recorded: ${new Date(m.created_at).toLocaleString()} • Duration: ${m.duration_seconds || 0}s`;

      document.getElementById('downloadPdfBtn').href = `/api/v1/meetings/${id}/pdf`;

      if (m.minutes) {
        document.getElementById('detailSentimentBadge').textContent = m.minutes.overall_sentiment || 'Productive';
        document.getElementById('detailExecutiveSummary').textContent = m.minutes.executive_summary;

        // Decisions
        const decEl = document.getElementById('detailDecisionsList');
        decEl.innerHTML = '';
        (m.minutes.key_decisions || []).forEach(d => {
          const li = document.createElement('li');
          li.textContent = d;
          decEl.appendChild(li);
        });

        // Actions
        const actionsEl = document.getElementById('detailActionsTable');
        actionsEl.innerHTML = '';
        (m.action_items || []).forEach(a => {
          const tr = document.createElement('tr');
          tr.className = 'hover:bg-slate-800/60 transition';
          tr.innerHTML = `
            <td class="px-4 py-3 font-medium text-slate-200">${a.task}</td>
            <td class="px-4 py-3 text-slate-300"><strong>${a.assignee_name}</strong> ${a.assignee_email ? '<span class="text-slate-400">(' + a.assignee_email + ')</span>' : ''}</td>
            <td class="px-4 py-3 text-slate-400">${a.due_date || 'TBD'}</td>
            <td class="px-4 py-3"><span class="px-2 py-0.5 rounded font-semibold text-[10px] ${a.priority === 'High' || a.priority === 'Urgent' ? 'bg-red-900/60 text-red-300' : 'bg-sky-900/60 text-sky-300'}">${a.priority}</span></td>
            <td class="px-4 py-3">
              <button onclick="toggleActionStatus(${a.id}, '${a.status}')" class="px-2 py-1 rounded text-[10px] font-semibold border ${a.status === 'Completed' ? 'border-emerald-600 bg-emerald-950/40 text-emerald-400' : 'border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500'}">
                ${a.status === 'Completed' ? '✓ Done' : 'Mark Done'}
              </button>
            </td>
          `;
          actionsEl.appendChild(tr);
        });

        // Topics
        const topicsEl = document.getElementById('detailTopicsList');
        topicsEl.innerHTML = '';
        (m.minutes.agenda_topics || []).forEach(t => {
          const div = document.createElement('div');
          div.className = 'bg-slate-900/40 border border-slate-800 p-3 rounded-xl';
          div.innerHTML = `
            <h4 class="font-semibold text-slate-200 text-xs">${t.topic}</h4>
            <p class="text-xs text-slate-400 mt-1">${t.summary}</p>
          `;
          topicsEl.appendChild(div);
        });

        // Verbatim Transcript Rendering
        currentTranscriptSegments = m.minutes.transcript || [];
        renderTranscript(currentTranscriptSegments);
      }
    }

    let currentTranscriptSegments = [];

    function renderTranscript(segments) {
      const el = document.getElementById('detailTranscriptList');
      el.innerHTML = '';

      if (!segments || segments.length === 0) {
        el.innerHTML = '<div class="text-xs text-slate-500 py-3 text-center italic">No speech transcript segments recorded.</div>';
        return;
      }

      segments.forEach((seg, index) => {
        const item = document.createElement('div');
        item.className = 'flex items-start gap-3 p-2.5 rounded-lg hover:bg-slate-800/50 transition border border-transparent hover:border-slate-800 text-xs';
        
        const isSpeakerA = index % 2 === 0;
        const badgeColor = isSpeakerA ? 'bg-sky-950/70 text-sky-300 border-sky-800' : 'bg-indigo-950/70 text-indigo-300 border-indigo-800';

        item.innerHTML = `
          <div class="flex items-center gap-2 shrink-0">
            <span class="text-[10px] font-mono text-slate-500 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">${seg.timestamp || '[00:00]'}</span>
            <span class="font-semibold px-2 py-0.5 rounded text-[10px] border ${badgeColor}">${seg.speaker || 'Speaker'}</span>
          </div>
          <p class="text-slate-300 leading-relaxed font-normal">${seg.text || ''}</p>
        `;
        el.appendChild(item);
      });
    }

    function filterTranscript() {
      const q = document.getElementById('transcriptSearchInput').value.toLowerCase().trim();
      if (!q) {
        renderTranscript(currentTranscriptSegments);
        return;
      }
      const filtered = currentTranscriptSegments.filter(s => 
        (s.text && s.text.toLowerCase().includes(q)) || 
        (s.speaker && s.speaker.toLowerCase().includes(q))
      );
      renderTranscript(filtered);
    }

    async function copyFullTranscript() {
      if (!currentTranscriptSegments || currentTranscriptSegments.length === 0) return;
      const text = currentTranscriptSegments.map(s => `${s.timestamp || ''} ${s.speaker || 'Speaker'}: ${s.text || ''}`).join('\\n');
      await navigator.clipboard.writeText(text);
      const btn = document.getElementById('copyTranscriptBtn');
      const orig = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i> Copied!';
      setTimeout(() => { btn.innerHTML = orig; }, 2000);
    }

    async function toggleActionStatus(actionId, currentStatus) {
      const nextStatus = currentStatus === 'Completed' ? 'Pending' : 'Completed';
      await fetch(`/api/v1/actions/${actionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus })
      });
      if (currentSelectedMeetingId) selectMeeting(currentSelectedMeetingId);
    }

    async function resendCurrentEmail() {
      if (!currentSelectedMeetingId) return;
      const btn = document.getElementById('resendEmailBtn');
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
      try {
        const res = await fetch(`/api/v1/meetings/${currentSelectedMeetingId}/email`, { method: 'POST' });
        const data = await res.json();
        alert(data.sent ? 'Recap email dispatched successfully!' : 'Email queued / SMTP host check completed.');
      } catch (e) {
        alert('Email error: ' + e.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Recap Email';
      }
    }

    async function handleAudioUpload(e) {
      e.preventDefault();
      const btn = document.getElementById('uploadSubmitBtn');
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing with Gemini...';

      const title = document.getElementById('uploadTitle').value;
      const rawParticipants = document.getElementById('uploadParticipants').value;
      const audioFile = document.getElementById('uploadAudioFile').files[0];
      const autoEmail = document.getElementById('uploadAutoEmail').checked;

      const participants = rawParticipants.split(',').filter(x => x.trim()).map(x => {
        const match = x.match(/(.*)\\((.*)\\)/);
        if (match) return { name: match[1].trim(), email: match[2].trim(), role: 'attendee' };
        return { name: x.trim(), email: null, role: 'attendee' };
      });

      const formData = new FormData();
      formData.append('audio_file', audioFile);
      formData.append('meeting_title', title);
      formData.append('participants_json', JSON.stringify(participants));
      formData.append('source', 'manual_upload');
      formData.append('auto_email', autoEmail ? 'true' : 'false');

      try {
        const res = await fetch('/api/v1/meetings/recordings', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        document.getElementById('uploadModal').classList.add('hidden');
        await loadMeetings();
        selectMeeting(data.meeting_id);
      } catch (err) {
        alert('Upload failed: ' + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>Process with Gemini</span>';
      }
    }

    // Check URL query parameters for ?meeting_id= or ?id=
    const urlParams = new URLSearchParams(window.location.search);
    const initialId = urlParams.get('meeting_id') || urlParams.get('id');
    if (initialId) {
      currentSelectedMeetingId = parseInt(initialId);
      selectMeeting(currentSelectedMeetingId);
    }

    // Initial Load & automatic real-time sync every 3 seconds
    loadMeetings();
    setInterval(loadMeetings, 3000);
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def root_dashboard():
    """Serves the interactive web management dashboard."""
    template_file = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_file):
        with open(template_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content=DASHBOARD_HTML)

@app.get("/health")
def health_check():
    """Health check endpoint for Kubernetes / Docker liveness probe."""
    return {"status": "healthy", "service": "gemini-meeting-agent", "environment": settings.ENVIRONMENT}

@app.get("/api/v1/extension/download")
def download_extension_zip():
    """Packages the Chrome Extension into an in-memory zip file and streams it for one-click download."""
    # Find the extension folder relative to backend
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    extension_dir = os.path.join(base_dir, "extension")
    if not os.path.isdir(extension_dir):
        # Fallback if running directly from project root or different cwd
        extension_dir = os.path.abspath(os.path.join(os.getcwd(), "extension"))
    
    if not os.path.isdir(extension_dir):
        raise HTTPException(status_code=404, detail="Extension directory not found on server")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(extension_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extension_dir)
                zip_file.write(file_path, arcname)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=meetflow-ai-extension.zip"
        }
    )

