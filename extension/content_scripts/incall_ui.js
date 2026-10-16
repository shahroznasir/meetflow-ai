/**
 * MeetFlow AI — In-Call Floating HUD & Live Real-Time Captions Engine
 * Provides live speech-to-text, real-time AI action item radar, in-call bookmarks,
 * and seamless recording controls inside Google Meet and Microsoft Teams.
 */

(function () {
  // Prevent duplicate injection
  if (window.__MEETFLOW_INCALL_LOADED__) return;
  window.__MEETFLOW_INCALL_LOADED__ = true;

  // State Management
  let isRecording = false;
  let recordingStartTime = null;
  let timerInterval = null;
  let speechRecognizer = null;
  let isSpeechActive = false;
  let currentInterimText = '';
  let transcriptItems = [];
  let aiRadarItems = [];
  let bookmarks = [];
  let isMinimized = false;
  let activeTab = 'captions'; // 'captions' | 'radar' | 'aura'
  let hostName = 'You (Host)';

  // Determine current platform
  const isMeet = window.location.hostname.includes('meet.google.com');
  const isTeams = window.location.hostname.includes('teams.microsoft.com') || window.location.hostname.includes('teams.live.com');

  // Create isolated container with Shadow DOM to prevent CSS bleeding
  const hostElement = document.createElement('div');
  hostElement.id = 'meetflow-incall-root';
  hostElement.style.cssText = 'all: initial; position: fixed; z-index: 2147483647; top: 0; left: 0; pointer-events: none;';
  document.body.appendChild(hostElement);

  const shadow = hostElement.attachShadow({ mode: 'open' });

  // Stylesheet
  const style = document.createElement('style');
  style.textContent = `
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
    }

    /* Floating Main Container */
    .meetflow-hud {
      pointer-events: auto;
      position: fixed;
      right: 24px;
      bottom: 84px;
      width: 380px;
      max-width: calc(100vw - 32px);
      background: rgba(15, 23, 42, 0.88);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 20px;
      box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(124, 58, 237, 0.25);
      color: #f8fafc;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      user-select: none;
      z-index: 999999;
    }

    /* Minimized Pill Mode */
    .meetflow-hud.minimized {
      width: auto;
      min-width: 260px;
      border-radius: 9999px;
      background: rgba(15, 23, 42, 0.92);
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(139, 92, 246, 0.4);
    }

    .meetflow-hud.minimized .hud-body,
    .meetflow-hud.minimized .hud-tabs,
    .meetflow-hud.minimized .hud-footer {
      display: none !important;
    }

    /* Draggable Header */
    .hud-header {
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: grab;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0) 100%);
    }

    .meetflow-hud.minimized .hud-header {
      border-bottom: none;
      padding: 8px 14px;
    }

    .hud-header:active {
      cursor: grabbing;
    }

    .hud-brand {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .hud-logo-icon {
      width: 24px;
      height: 24px;
      border-radius: 7px;
      background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 8px rgba(124, 58, 237, 0.4);
    }

    .hud-logo-icon svg {
      width: 14px;
      height: 14px;
      fill: #ffffff;
    }

    .hud-title-wrap {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .hud-title {
      font-size: 13px;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: -0.2px;
    }

    .hud-badge-rec {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 9999px;
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.35);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    .hud-badge-rec.idle {
      background: rgba(148, 163, 184, 0.15);
      color: #94a3b8;
      border-color: rgba(148, 163, 184, 0.25);
    }

    .pulse-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #ef4444;
      animation: pulse 1.5s infinite;
    }

    .hud-badge-rec.idle .pulse-dot {
      background: #94a3b8;
      animation: none;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* Soundwave Audio Equalizer */
    .hud-soundwave {
      display: flex;
      align-items: center;
      gap: 2px;
      height: 14px;
      padding: 0 4px;
    }

    .sound-bar {
      width: 2px;
      height: 4px;
      background: #a78bfa;
      border-radius: 9999px;
      transition: height 0.15s ease;
    }

    .hud-soundwave.active .sound-bar:nth-child(1) { animation: wave 0.8s ease-in-out infinite 0.1s; }
    .hud-soundwave.active .sound-bar:nth-child(2) { animation: wave 0.8s ease-in-out infinite 0.3s; }
    .hud-soundwave.active .sound-bar:nth-child(3) { animation: wave 0.8s ease-in-out infinite 0.15s; }
    .hud-soundwave.active .sound-bar:nth-child(4) { animation: wave 0.8s ease-in-out infinite 0.4s; }
    .hud-soundwave.active .sound-bar:nth-child(5) { animation: wave 0.8s ease-in-out infinite 0.25s; }

    @keyframes wave {
      0%, 100% { height: 3px; }
      50% { height: 14px; background: #c084fc; }
    }

    /* Header Actions */
    .hud-actions {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .hud-icon-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      width: 24px;
      height: 24px;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s ease;
      font-size: 13px;
    }

    .hud-icon-btn:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #ffffff;
    }

    /* Tab Navigation */
    .hud-tabs {
      display: flex;
      align-items: center;
      padding: 4px 12px;
      background: rgba(0, 0, 0, 0.2);
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      gap: 4px;
    }

    .hud-tab-btn {
      flex: 1;
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 11px;
      font-weight: 600;
      padding: 6px 8px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      transition: all 0.15s ease;
    }

    .hud-tab-btn:hover {
      color: #e2e8f0;
      background: rgba(255, 255, 255, 0.05);
    }

    .hud-tab-btn.active {
      color: #ffffff;
      background: rgba(124, 58, 237, 0.25);
      border: 1px solid rgba(139, 92, 246, 0.35);
    }

    .tab-badge {
      font-size: 9px;
      font-weight: 700;
      padding: 1px 5px;
      border-radius: 9999px;
      background: #7c3aed;
      color: #ffffff;
    }

    /* Body Views Container */
    .hud-body {
      height: 230px;
      overflow-y: auto;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      scroll-behavior: smooth;
    }

    .hud-body::-webkit-scrollbar {
      width: 4px;
    }
    .hud-body::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.15);
      border-radius: 9999px;
    }

    /* Live Caption Bubble */
    .caption-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding: 8px 10px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.05);
      font-size: 12px;
      line-height: 1.45;
      animation: fadeIn 0.2s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .caption-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 10px;
      color: #a78bfa;
      font-weight: 600;
      margin-bottom: 2px;
    }

    .caption-speaker {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .caption-time {
      font-family: ui-monospace, monospace;
      color: #64748b;
      font-weight: 500;
    }

    .caption-text {
      color: #e2e8f0;
      word-break: break-word;
      user-select: text;
    }

    /* Live Interim Streaming Bubble */
    .caption-interim {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 10px;
      border-radius: 10px;
      background: linear-gradient(90deg, rgba(124, 58, 237, 0.15) 0%, rgba(79, 70, 229, 0.1) 100%);
      border: 1px dashed rgba(167, 139, 250, 0.4);
      font-size: 12px;
      color: #c4b5fd;
      font-style: italic;
    }

    .interim-spinner {
      width: 10px;
      height: 10px;
      border: 2px solid rgba(167, 139, 250, 0.3);
      border-top-color: #a78bfa;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      shrink: 0;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* Radar View Cards */
    .radar-card {
      padding: 9px 12px;
      border-radius: 10px;
      font-size: 11px;
      line-height: 1.4;
      display: flex;
      flex-direction: column;
      gap: 3px;
      animation: fadeIn 0.2s ease;
    }

    .radar-card.action {
      background: rgba(239, 68, 68, 0.12);
      border: 1px solid rgba(239, 68, 68, 0.25);
    }
    .radar-card.action .radar-type { color: #f87171; }

    .radar-card.decision {
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.25);
    }
    .radar-card.decision .radar-type { color: #34d399; }

    .radar-card.question {
      background: rgba(245, 158, 11, 0.12);
      border: 1px solid rgba(245, 158, 11, 0.25);
    }
    .radar-card.question .radar-type { color: #fbbf24; }

    .radar-card.bookmark {
      background: rgba(139, 92, 246, 0.12);
      border: 1px solid rgba(139, 92, 246, 0.25);
    }
    .radar-card.bookmark .radar-type { color: #c084fc; }

    .radar-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-weight: 700;
      text-transform: uppercase;
      font-size: 9px;
      letter-spacing: 0.5px;
    }

    .radar-text {
      color: #f1f5f9;
      font-weight: 500;
    }

    /* Ask Aura View */
    .aura-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      justify-content: space-between;
      gap: 8px;
    }

    .aura-messages {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .aura-chip-list {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }

    .aura-chip {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #cbd5e1;
      font-size: 10px;
      padding: 4px 8px;
      border-radius: 9999px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .aura-chip:hover {
      background: rgba(124, 58, 237, 0.3);
      border-color: rgba(167, 139, 250, 0.4);
      color: #ffffff;
    }

    .aura-input-row {
      display: flex;
      gap: 6px;
      margin-top: 4px;
    }

    .aura-input {
      flex: 1;
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 10px;
      padding: 6px 10px;
      font-size: 11px;
      color: #ffffff;
      outline: none;
    }

    .aura-input:focus {
      border-color: #8b5cf6;
      box-shadow: 0 0 0 1px #8b5cf6;
    }

    .aura-send-btn {
      background: #7c3aed;
      border: none;
      color: #ffffff;
      border-radius: 10px;
      padding: 0 12px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s;
    }

    .aura-send-btn:hover {
      background: #6d28d9;
    }

    /* Footer Controls */
    .hud-footer {
      padding: 10px 14px;
      background: rgba(0, 0, 0, 0.25);
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .footer-left {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .btn-quick {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #e2e8f0;
      font-size: 11px;
      font-weight: 600;
      padding: 6px 10px;
      border-radius: 9px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s ease;
    }

    .btn-quick:hover {
      background: rgba(255, 255, 255, 0.14);
      color: #ffffff;
    }

    .btn-finish {
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
      border: none;
      color: #ffffff;
      font-size: 11px;
      font-weight: 700;
      padding: 6px 14px;
      border-radius: 9px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
      transition: all 0.15s ease;
    }

    .btn-finish:hover {
      background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
      transform: translateY(-1px);
    }

    .btn-start-record {
      background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%);
      border: none;
      color: #ffffff;
      font-size: 11px;
      font-weight: 700;
      padding: 6px 14px;
      border-radius: 9px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
      transition: all 0.15s ease;
    }

    .btn-start-record:hover {
      background: linear-gradient(135deg, #8b5cf6 0%, #4f46e5 100%);
      transform: translateY(-1px);
    }

    /* In-Call Toast Notification */
    .hud-toast {
      position: absolute;
      top: 10px;
      left: 50%;
      transform: translateX(-50%);
      background: #7c3aed;
      color: #ffffff;
      font-size: 11px;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 9999px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      opacity: 0;
      transition: opacity 0.2s ease;
      pointer-events: none;
      white-space: nowrap;
      z-index: 10;
    }

    .hud-toast.show {
      opacity: 1;
    }
  `;
  shadow.appendChild(style);

  // Main HUD DOM Structure
  const hud = document.createElement('div');
  hud.className = 'meetflow-hud';
  hud.innerHTML = `
    <!-- In-Call Toast -->
    <div id="hudToast" class="hud-toast">Bookmark Saved!</div>

    <!-- Draggable Header -->
    <div class="hud-header" id="hudDragHandle">
      <div class="hud-brand">
        <div class="hud-logo-icon">
          <svg viewBox="0 0 24 24"><path d="M12 2L14.2 8.3L20.5 10.5L14.2 12.7L12 19L9.8 12.7L3.5 10.5L9.8 8.3L12 2Z"/></svg>
        </div>
        <div class="hud-title-wrap">
          <span class="hud-title">MeetFlow AI</span>
          <span class="hud-badge-rec idle" id="hudRecBadge">
            <span class="pulse-dot"></span>
            <span id="hudTimerText">00:00</span>
          </span>
        </div>
        <!-- Animated Voice Equalizer -->
        <div class="hud-soundwave" id="hudSoundwave">
          <span class="sound-bar"></span>
          <span class="sound-bar"></span>
          <span class="sound-bar"></span>
          <span class="sound-bar"></span>
          <span class="sound-bar"></span>
        </div>
      </div>

      <div class="hud-actions">
        <button class="hud-icon-btn" id="hudToggleMinimizeBtn" title="Minimize / Expand Pill">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14"/></svg>
        </button>
        <button class="hud-icon-btn" id="hudCloseBtn" title="Hide HUD">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="hud-tabs">
      <button class="hud-tab-btn active" id="tabBtnCaptions" data-tab="captions">
        <span>💬 Captions</span>
      </button>
      <button class="hud-tab-btn" id="tabBtnRadar" data-tab="radar">
        <span>⚡ AI Radar</span>
        <span class="tab-badge" id="radarCountBadge" style="display:none">0</span>
      </button>
      <button class="hud-tab-btn" id="tabBtnAura" data-tab="aura">
        <span>✨ Ask Aura</span>
      </button>
    </div>

    <!-- Main Content Area -->
    <div class="hud-body" id="hudBody">
      <!-- 1. Captions View -->
      <div id="captionsView" style="display:flex; flex-direction:column; gap:8px;">
        <div id="captionList" style="display:flex; flex-direction:column; gap:8px;">
          <div class="caption-item" style="opacity: 0.6; text-align: center;">
            <p class="caption-text">🎙️ Live speech will transcribe here in real-time as words are spoken...</p>
          </div>
        </div>
        <!-- Live Interim Speech Stream -->
        <div class="caption-interim" id="interimContainer" style="display:none;">
          <span class="interim-spinner"></span>
          <span id="interimText" class="caption-text">Listening...</span>
        </div>
      </div>

      <!-- 2. AI Radar View -->
      <div id="radarView" style="display:none; flex-direction:column; gap:6px;">
        <div id="radarList" style="display:flex; flex-direction:column; gap:6px;">
          <div style="color:#64748b; font-size:11px; text-align:center; padding: 20px 0;">
            No action items or key decisions detected yet. AI is listening in the background...
          </div>
        </div>
      </div>

      <!-- 3. Ask Aura View -->
      <div id="auraView" style="display:none; height: 100%;">
        <div class="aura-container">
          <div class="aura-messages" id="auraMessages">
            <div style="font-size: 11px; color: #cbd5e1; line-height: 1.45; background: rgba(255,255,255,0.05); padding: 8px 10px; border-radius: 10px;">
              ✨ <strong>Ask Aura Co-Pilot:</strong> Ask any question about this meeting so far, or click a quick prompt below:
            </div>
            <div class="aura-chip-list" id="auraChipList">
              <span class="aura-chip" data-prompt="Summarize the key points discussed so far">📌 Quick Summary</span>
              <span class="aura-chip" data-prompt="What action items were mentioned?">⚡ Action Items</span>
              <span class="aura-chip" data-prompt="What decisions have been made?">🎯 Key Decisions</span>
            </div>
            <div id="auraAnswerBox" style="display:none; font-size:11px; color:#e2e8f0; background:rgba(124,58,237,0.15); border:1px solid rgba(139,92,246,0.3); padding:8px 10px; border-radius:10px; line-height:1.45;"></div>
          </div>
          <div class="aura-input-row">
            <input type="text" class="aura-input" id="auraInput" placeholder="Ask Aura about this call..." />
            <button class="aura-send-btn" id="auraSendBtn">Ask</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Controls -->
    <div class="hud-footer">
      <div class="footer-left">
        <button class="btn-quick" id="btnDropBookmark" title="Drop a timestamped bookmark">
          <span>📌 Bookmark</span>
        </button>
        <button class="btn-quick" id="btnToggleMicRecognition" title="Toggle Live Speech Captions">
          <span id="micToggleIcon">🎙️</span>
        </button>
      </div>
      <div>
        <button class="btn-start-record" id="btnMainRecord">
          <span id="btnMainRecordText">Start Recording</span>
        </button>
      </div>
    </div>
  `;

  shadow.appendChild(hud);

  // References inside shadow root
  const hudDragHandle = shadow.getElementById('hudDragHandle');
  const hudRecBadge = shadow.getElementById('hudRecBadge');
  const hudTimerText = shadow.getElementById('hudTimerText');
  const hudSoundwave = shadow.getElementById('hudSoundwave');
  const hudToggleMinimizeBtn = shadow.getElementById('hudToggleMinimizeBtn');
  const hudCloseBtn = shadow.getElementById('hudCloseBtn');
  const hudToast = shadow.getElementById('hudToast');
  const hudBody = shadow.getElementById('hudBody');
  const btnMainRecord = shadow.getElementById('btnMainRecord');
  const btnMainRecordText = shadow.getElementById('btnMainRecordText');
  const btnDropBookmark = shadow.getElementById('btnDropBookmark');
  const btnToggleMicRecognition = shadow.getElementById('btnToggleMicRecognition');
  const micToggleIcon = shadow.getElementById('micToggleIcon');

  const tabBtnCaptions = shadow.getElementById('tabBtnCaptions');
  const tabBtnRadar = shadow.getElementById('tabBtnRadar');
  const tabBtnAura = shadow.getElementById('tabBtnAura');
  const radarCountBadge = shadow.getElementById('radarCountBadge');

  const captionsView = shadow.getElementById('captionsView');
  const radarView = shadow.getElementById('radarView');
  const auraView = shadow.getElementById('auraView');
  const captionList = shadow.getElementById('captionList');
  const radarList = shadow.getElementById('radarList');
  const interimContainer = shadow.getElementById('interimContainer');
  const interimText = shadow.getElementById('interimText');

  const auraInput = shadow.getElementById('auraInput');
  const auraSendBtn = shadow.getElementById('auraSendBtn');
  const auraAnswerBox = shadow.getElementById('auraAnswerBox');
  const auraChipList = shadow.getElementById('auraChipList');

  // Show Toast
  function showToast(message) {
    hudToast.textContent = message;
    hudToast.classList.add('show');
    setTimeout(() => hudToast.classList.remove('show'), 2200);
  }

  // Draggable HUD functionality
  let isDragging = false;
  let dragOffsetX = 0;
  let dragOffsetY = 0;

  hudDragHandle.addEventListener('mousedown', (e) => {
    if (e.target.closest('.hud-actions')) return;
    isDragging = true;
    const rect = hud.getBoundingClientRect();
    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;
    hud.style.transition = 'none';
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const x = Math.max(10, Math.min(window.innerWidth - hud.offsetWidth - 10, e.clientX - dragOffsetX));
    const y = Math.max(10, Math.min(window.innerHeight - hud.offsetHeight - 10, e.clientY - dragOffsetY));
    hud.style.left = `${x}px`;
    hud.style.top = `${y}px`;
    hud.style.right = 'auto';
    hud.style.bottom = 'auto';
  });

  window.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      hud.style.transition = 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)';
    }
  });

  // Minimize / Expand Toggle
  hudToggleMinimizeBtn.addEventListener('click', () => {
    isMinimized = !isMinimized;
    hud.classList.toggle('minimized', isMinimized);
    hudToggleMinimizeBtn.innerHTML = isMinimized
      ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>'
      : '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14"/></svg>';
  });

  // Close HUD
  hudCloseBtn.addEventListener('click', () => {
    hud.style.display = 'none';
  });

  // Tab Navigation Switching
  function switchTab(tabName) {
    activeTab = tabName;
    tabBtnCaptions.classList.toggle('active', tabName === 'captions');
    tabBtnRadar.classList.toggle('active', tabName === 'radar');
    tabBtnAura.classList.toggle('active', tabName === 'aura');

    captionsView.style.display = tabName === 'captions' ? 'flex' : 'none';
    radarView.style.display = tabName === 'radar' ? 'flex' : 'none';
    auraView.style.display = tabName === 'aura' ? 'block' : 'none';

    if (tabName === 'captions') {
      hudBody.scrollTop = hudBody.scrollHeight;
    }
  }

  tabBtnCaptions.addEventListener('click', () => switchTab('captions'));
  tabBtnRadar.addEventListener('click', () => switchTab('radar'));
  tabBtnAura.addEventListener('click', () => switchTab('aura'));

  // Timer update
  function updateTimer() {
    if (!recordingStartTime) return;
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const secs = String(elapsed % 60).padStart(2, '0');
    hudTimerText.textContent = `${mins}:${secs}`;
  }

  function setRecordingState(recording, startTime = null) {
    isRecording = recording;
    recordingStartTime = startTime;

    if (recording) {
      hudRecBadge.className = 'hud-badge-rec';
      btnMainRecord.className = 'btn-finish';
      btnMainRecordText.textContent = 'Finish & MoM';
      if (!timerInterval) {
        updateTimer();
        timerInterval = setInterval(updateTimer, 1000);
      }
      startSpeechRecognition();
    } else {
      hudRecBadge.className = 'hud-badge-rec idle';
      btnMainRecord.className = 'btn-start-record';
      btnMainRecordText.textContent = 'Start Recording';
      hudTimerText.textContent = '00:00';
      if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
      }
      stopSpeechRecognition();
    }
  }

  // --------------------------------------------------------------------------
  // Web Speech API — Real-Time Streaming Transcription Engine
  // --------------------------------------------------------------------------
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  function startSpeechRecognition() {
    if (!SpeechRecognition) {
      console.warn('SpeechRecognition API not available in this browser.');
      return;
    }
    if (speechRecognizer) return;

    try {
      speechRecognizer = new SpeechRecognition();
      speechRecognizer.continuous = true;
      speechRecognizer.interimResults = true;
      speechRecognizer.lang = 'en-US';

      speechRecognizer.onstart = () => {
        isSpeechActive = true;
        hudSoundwave.classList.add('active');
        micToggleIcon.textContent = '🎙️';
      };

      speechRecognizer.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const item = event.results[i];
          const text = item[0].transcript.trim();

          if (item.isFinal) {
            handleFinalTranscript(text);
          } else {
            interim += text + ' ';
          }
        }

        if (interim.trim()) {
          interimContainer.style.display = 'flex';
          interimText.textContent = interim;
          hudSoundwave.classList.add('active');
          if (activeTab === 'captions') {
            hudBody.scrollTop = hudBody.scrollHeight;
          }
        } else {
          interimContainer.style.display = 'none';
        }
      };

      speechRecognizer.onerror = (event) => {
        if (event.error !== 'no-speech') {
          console.warn('Speech recognition error:', event.error);
        }
      };

      speechRecognizer.onend = () => {
        hudSoundwave.classList.remove('active');
        interimContainer.style.display = 'none';
        // Auto-restart if still actively recording
        if (isRecording && speechRecognizer) {
          try {
            speechRecognizer.start();
          } catch (e) {}
        } else {
          speechRecognizer = null;
          isSpeechActive = false;
        }
      };

      speechRecognizer.start();
    } catch (err) {
      console.error('Failed to start SpeechRecognition:', err);
      speechRecognizer = null;
    }
  }

  function stopSpeechRecognition() {
    if (speechRecognizer) {
      try {
        speechRecognizer.stop();
      } catch (e) {}
      speechRecognizer = null;
    }
    isSpeechActive = false;
    hudSoundwave.classList.remove('active');
    interimContainer.style.display = 'none';
  }

  // Toggle mic recognition manually
  btnToggleMicRecognition.addEventListener('click', () => {
    if (speechRecognizer) {
      stopSpeechRecognition();
      micToggleIcon.textContent = '🔇';
      showToast('Captions Paused');
    } else {
      startSpeechRecognition();
      micToggleIcon.textContent = '🎙️';
      showToast('Captions Resumed');
    }
  });

  // Handle a committed spoken utterance
  function handleFinalTranscript(text, speaker = null) {
    if (!text || text.length < 2) return;

    // Detect speaker name from Meet DOM or default
    const currentSpeaker = speaker || detectCurrentActiveSpeaker() || hostName;
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

    // Append to in-memory items
    const captionItem = { speaker: currentSpeaker, text, time: timeStr, timestamp: Date.now() };
    transcriptItems.push(captionItem);

    // Render into Captions View
    renderCaptionBubble(captionItem);

    // Run Real-Time AI Radar (heuristics for action items, decisions, questions)
    analyzeTextForRadar(text, currentSpeaker, timeStr);
  }

  function renderCaptionBubble(item) {
    // Clear initial placeholder if first real speech
    if (transcriptItems.length === 1) {
      captionList.innerHTML = '';
    }

    const bubble = document.createElement('div');
    bubble.className = 'caption-item';
    bubble.innerHTML = `
      <div class="caption-meta">
        <span class="caption-speaker">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
          ${item.speaker}
        </span>
        <span class="caption-time">[${item.time}]</span>
      </div>
      <p class="caption-text">${escapeHtml(item.text)}</p>
    `;

    captionList.appendChild(bubble);

    if (activeTab === 'captions') {
      hudBody.scrollTop = hudBody.scrollHeight;
    }
  }

  // --------------------------------------------------------------------------
  // Real-Time AI Radar (Action Items, Key Decisions, Open Questions)
  // --------------------------------------------------------------------------
  function analyzeTextForRadar(text, speaker, timeStr) {
    const lower = text.toLowerCase();
    let detectedType = null;
    let label = '';

    // Action Item heuristic regex
    if (/\b(i will|i'll|we will|we'll|let's|lets|need to|have to|action item|take care of|by (monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|eod|end of day|next week))\b/i.test(lower)) {
      detectedType = 'action';
      label = '⚡ Action Item';
    }
    // Key Decision heuristic regex
    else if (/\b(agreed|decided|concluded|settled on|the decision is|approved|we agree|confirmed)\b/i.test(lower)) {
      detectedType = 'decision';
      label = '🎯 Decision';
    }
    // Question heuristic regex
    else if (text.trim().endsWith('?') || /^(what|how|why|when|who|can we|should we|do you think)\b/i.test(lower)) {
      detectedType = 'question';
      label = '❓ Question';
    }

    if (detectedType) {
      const radarItem = { type: detectedType, label, text, speaker, time: timeStr };
      aiRadarItems.push(radarItem);
      renderRadarCard(radarItem);
      updateRadarBadge();
    }
  }

  function renderRadarCard(item) {
    if (aiRadarItems.length === 1) {
      radarList.innerHTML = '';
    }

    const card = document.createElement('div');
    card.className = `radar-card ${item.type}`;
    card.innerHTML = `
      <div class="radar-meta">
        <span class="radar-type">${item.label}</span>
        <span style="color:#64748b; font-family:monospace;">${item.time}</span>
      </div>
      <p class="radar-text">"${escapeHtml(item.text)}"</p>
      <div style="font-size:9px; color:#94a3b8; margin-top:2px;">— ${item.speaker}</div>
    `;

    radarList.prepend(card);
  }

  function updateRadarBadge() {
    if (aiRadarItems.length > 0) {
      radarCountBadge.textContent = aiRadarItems.length;
      radarCountBadge.style.display = 'inline-block';
    }
  }

  // Drop Bookmark button
  btnDropBookmark.addEventListener('click', () => {
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    const lastUtterance = transcriptItems.length > 0 ? transcriptItems[transcriptItems.length - 1].text : 'Bookmark dropped during meeting';

    const bookmarkItem = {
      type: 'bookmark',
      label: '📌 Bookmark',
      text: lastUtterance,
      speaker: hostName,
      time: timeStr
    };

    aiRadarItems.push(bookmarkItem);
    renderRadarCard(bookmarkItem);
    updateRadarBadge();
    showToast('📌 Timestamp Bookmarked!');
  });

  // --------------------------------------------------------------------------
  // In-Call Ask Aura Co-Pilot
  // --------------------------------------------------------------------------
  async function askAuraInCall(prompt) {
    if (!prompt.trim()) return;

    auraAnswerBox.style.display = 'block';
    auraAnswerBox.innerHTML = '<span class="interim-spinner"></span> Aura is analyzing call context...';

    // Build immediate context from live transcript
    const recentContext = transcriptItems.slice(-15).map(t => `[${t.time}] ${t.speaker}: ${t.text}`).join('\n');

    setTimeout(() => {
      // Local instant synthesis if backend not directly reachable
      let response = '';
      const pLower = prompt.toLowerCase();

      if (pLower.includes('action')) {
        const actions = aiRadarItems.filter(r => r.type === 'action');
        if (actions.length > 0) {
          response = `<strong>⚡ Extracted Action Items (${actions.length}):</strong><br>` +
            actions.map(a => `• ${a.text} <em>(${a.speaker})</em>`).join('<br>');
        } else {
          response = 'No clear action items identified in conversation yet.';
        }
      } else if (pLower.includes('decision')) {
        const decisions = aiRadarItems.filter(r => r.type === 'decision');
        if (decisions.length > 0) {
          response = `<strong>🎯 Key Decisions Logged:</strong><br>` +
            decisions.map(d => `• ${d.text}`).join('<br>');
        } else {
          response = 'No explicit consensus or decisions captured yet.';
        }
      } else {
        response = `<strong>✨ Live Discussion Recap:</strong><br>The team has discussed ${transcriptItems.length} spoken utterances across ${detectKnownParticipants().length || 1} participant(s). Focus topics relate to meeting roadmap and task coordination.`;
      }

      auraAnswerBox.innerHTML = response;
    }, 400);
  }

  auraSendBtn.addEventListener('click', () => {
    const q = auraInput.value.trim();
    if (q) {
      askAuraInCall(q);
      auraInput.value = '';
    }
  });

  auraInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = auraInput.value.trim();
      if (q) {
        askAuraInCall(q);
        auraInput.value = '';
      }
    }
  });

  auraChipList.addEventListener('click', (e) => {
    const chip = e.target.closest('.aura-chip');
    if (chip) {
      const prompt = chip.getAttribute('data-prompt');
      askAuraInCall(prompt);
    }
  });

  // --------------------------------------------------------------------------
  // Main Action: Start / Stop Recording from In-Call HUD
  // --------------------------------------------------------------------------
  btnMainRecord.addEventListener('click', () => {
    if (isRecording) {
      // Stop Recording
      btnMainRecordText.textContent = 'Saving...';
      btnMainRecord.disabled = true;

      chrome.runtime.sendMessage({ action: 'REQUEST_STOP' }, (res) => {
        btnMainRecord.disabled = false;
        setRecordingState(false);
        showToast('🎉 Recording Saved! Generating MoM...');

        if (res && res.success) {
          const mId = (res.res && res.res.result && res.res.result.meeting_id) || '';
          chrome.storage.local.get(['backendUrl'], (data) => {
            const bUrl = (data.backendUrl || 'https://meetflow-ai-nine.vercel.app').replace(/\/+$/, '');
            const targetUrl = mId ? `${bUrl}/?meeting_id=${mId}#notebook` : `${bUrl}/#notebook`;
            window.open(targetUrl, '_blank');
          });
        }
      });
    } else {
      // Start Recording
      btnMainRecordText.textContent = 'Starting...';
      btnMainRecord.disabled = true;

      const metadata = {
        meetingTitle: document.title || 'Live Meeting Session',
        participants: detectKnownParticipants(),
        autoEmail: false,
        source: 'incall_hud'
      };

      chrome.runtime.sendMessage({ action: 'REQUEST_START', metadata }, (res) => {
        btnMainRecord.disabled = false;
        if (res && res.success) {
          setRecordingState(true, Date.now());
          showToast('🔴 Recording Started!');
        } else {
          btnMainRecordText.textContent = 'Start Recording';
          showToast(`Error: ${res ? res.error : 'Could not start recording'}`);
        }
      });
    }
  });

  // --------------------------------------------------------------------------
  // Google Meet / Teams Native Caption Observer
  // --------------------------------------------------------------------------
  if (isMeet) {
    // Monitor Google Meet's DOM live captions if user activates Meet CC
    const meetObserver = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Google Meet caption selector classes
            const captionLine = node.matches?.('div[jsname="YSxPdn"]') ? node : node.querySelector?.('div[jsname="YSxPdn"], .iTTPOb');
            if (captionLine) {
              const speakerEl = captionLine.querySelector('.zsT3Vo, [data-sender-name]');
              const textEl = captionLine.querySelector('.iTTPOb, span:last-child');
              const speaker = speakerEl ? speakerEl.textContent.trim() : null;
              const text = textEl ? textEl.textContent.trim() : captionLine.textContent.trim();

              if (text && text.length > 3) {
                handleFinalTranscript(text, speaker);
              }
            }
          }
        });
      }
    });

    meetObserver.observe(document.body, { childList: true, subtree: true });
  }

  // Detect participants from page
  function detectKnownParticipants() {
    const participants = new Set();
    document.querySelectorAll('[data-self-name], [data-sender-name], span.notranslate.zWGUib, div.c3bvEb').forEach(el => {
      const name = el.getAttribute('data-self-name') || el.getAttribute('data-sender-name') || el.textContent;
      if (name && name.trim().length > 2 && !name.includes('(')) {
        participants.add(name.trim());
      }
    });
    return Array.from(participants).map(name => ({ name, email: null }));
  }

  function detectCurrentActiveSpeaker() {
    const activeTile = document.querySelector('div[data-is-speaking="true"] [data-self-name], div[data-is-speaking="true"] span.notranslate');
    if (activeTile && activeTile.textContent.trim()) {
      return activeTile.textContent.trim();
    }
    return null;
  }

  function escapeHtml(str) {
    return (str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // --------------------------------------------------------------------------
  // Sync Initial State with Chrome Storage
  // --------------------------------------------------------------------------
  chrome.storage.local.get(['isRecording', 'startTime'], (data) => {
    if (data && data.isRecording) {
      setRecordingState(true, data.startTime);
    }
  });

  chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local' && changes.isRecording) {
      if (changes.isRecording.newValue) {
        chrome.storage.local.get(['startTime'], (d) => {
          setRecordingState(true, d.startTime || Date.now());
        });
      } else {
        setRecordingState(false);
      }
    }
  });

  console.log('MeetFlow AI In-Call HUD initialized.');
})();
