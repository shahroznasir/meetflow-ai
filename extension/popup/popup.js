// MeetFlow AI — Interactive Popup Controller (Fireflies Theme)

let timerInterval = null;
let recordingStartTime = null;
let micTestStream = null;
let micTestAudioContext = null;
let micTestAnimationId = null;
let liveBookmarks = [];

const ICEBREAKERS = [
  "⚡ 'What was your biggest unexpected win or breakthrough this week?'",
  "☕ 'Quick check-in: Coffee, tea, or pure adrenaline powering your day?'",
  "🎯 'If you had one extra hour today, what project would you tackle first?'",
  "🚀 'What is the #1 outcome that would make today a success for you?'",
  "🌍 'If you could work from anywhere in the world next week, where would you go?'"
];

let icebreakerIndex = 0;

document.addEventListener('DOMContentLoaded', async () => {
  const statusBadge = document.getElementById('statusBadge');
  const meetingTitleInput = document.getElementById('meetingTitleInput');
  const participantList = document.getElementById('participantList');
  const addParticipantBtn = document.getElementById('addParticipantBtn');
  const attendeeCountBadge = document.getElementById('attendeeCountBadge');
  const autoEmailToggle = document.getElementById('autoEmailToggle');
  const backendUrlInput = document.getElementById('backendUrlInput');
  const timerContainer = document.getElementById('timerContainer');
  const recordingTimer = document.getElementById('recordingTimer');
  const alertBox = document.getElementById('alertBox');
  const recordBtn = document.getElementById('recordBtn');
  const dashboardLink = document.getElementById('dashboardLink');
  const micNoticeBox = document.getElementById('micNoticeBox');
  const openMicPermissionBtn = document.getElementById('openMicPermissionBtn');
  const platformPill = document.getElementById('platformPill');
  const platformLabel = document.getElementById('platformLabel');
  const serverDot = document.getElementById('serverDot');
  const serverStatusText = document.getElementById('serverStatusText');
  const micTestBtn = document.getElementById('micTestBtn');
  const micMonitorBar = document.getElementById('micMonitorBar');
  const micQualityTag = document.getElementById('micQualityTag');
  const micTestText = document.getElementById('micTestText');
  const micTestIcon = document.getElementById('micTestIcon');
  const vuBars = document.querySelectorAll('.vu-bar');
  const bookmarkButtons = document.querySelectorAll('.btn-bookmark');
  const liveBookmarksList = document.getElementById('liveBookmarksList');
  const bookmarkCount = document.getElementById('bookmarkCount');
  const prepAgendaBtn = document.getElementById('prepAgendaBtn');
  const prepIcebreakerBtn = document.getElementById('prepIcebreakerBtn');
  const auraPrepOutput = document.getElementById('auraPrepOutput');
  const synthesisCard = document.getElementById('synthesisCard');
  const synDuration = document.getElementById('synDuration');
  const synAttendees = document.getElementById('synAttendees');
  const synNotebookBtn = document.getElementById('synNotebookBtn');
  const copyMeetingLinkBtn = document.getElementById('copyMeetingLinkBtn');
  const copyLinkText = document.getElementById('copyLinkText');
  const copyLinkIcon = document.getElementById('copyLinkIcon');
  const startNewMeetingBtn = document.getElementById('startNewMeetingBtn');

  // Compute initials for avatar bubbles
  function getInitials(name) {
    if (!name || !name.trim()) return '?';
    const words = name.trim().split(/\s+/);
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return words[0].slice(0, 2).toUpperCase();
  }

  // Update attendee count badge
  function updateAttendeeCount() {
    if (!attendeeCountBadge) return;
    const count = participantList ? participantList.querySelectorAll('.participant-row').length : 0;
    attendeeCountBadge.textContent = `${count} ${count === 1 ? 'attendee' : 'attendees'}`;
  }

  // --------------------------------------------------------------------------
  // Interactive Live Microphone VU Meter
  // --------------------------------------------------------------------------
  async function toggleMicTest() {
    if (micTestStream) {
      stopMicTest();
      return;
    }

    try {
      micTestBtn.classList.add('active');
      micTestText.textContent = 'Listening...';
      micQualityTag.textContent = 'Calibrating signal...';
      micMonitorBar.classList.add('active');

      micTestStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      micTestAudioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = micTestAudioContext.createMediaStreamSource(micTestStream);
      const analyser = micTestAudioContext.createAnalyser();
      analyser.fftSize = 32;
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      function renderVU() {
        if (!micTestStream) return;
        analyser.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;

        // Dynamically scale VU bars based on volume
        vuBars.forEach((bar, index) => {
          const val = dataArray[index % bufferLength] || avg;
          const height = Math.max(3, Math.min(15, Math.round((val / 255) * 15)));
          bar.style.height = `${height}px`;
        });

        if (avg > 30) {
          micQualityTag.innerHTML = `<span style="color:#059669; font-weight:700;">🟢 Good Speech Signal (${Math.round(avg)}dB)</span>`;
        } else if (avg > 5) {
          micQualityTag.innerHTML = `<span style="color:#D97706; font-weight:600;">🟡 Quiet Voice Detected</span>`;
        } else {
          micQualityTag.innerHTML = `<span style="color:#64748B;">Listening... speak to test</span>`;
        }

        micTestAnimationId = requestAnimationFrame(renderVU);
      }

      renderVU();
    } catch (err) {
      console.warn('Mic test error:', err);
      stopMicTest();
      micQualityTag.textContent = 'Mic access unavailable';
    }
  }

  function stopMicTest() {
    if (micTestAnimationId) {
      cancelAnimationFrame(micTestAnimationId);
      micTestAnimationId = null;
    }
    if (micTestStream) {
      micTestStream.getTracks().forEach((t) => t.stop());
      micTestStream = null;
    }
    if (micTestAudioContext && micTestAudioContext.state !== 'closed') {
      micTestAudioContext.close().catch(() => {});
      micTestAudioContext = null;
    }

    micTestBtn.classList.remove('active');
    micTestText.textContent = 'Live Mic Check';
    micMonitorBar.classList.remove('active');
    micQualityTag.textContent = 'Click to test levels';
    vuBars.forEach((bar) => { bar.style.height = '4px'; });
  }

  if (micTestBtn) {
    micTestBtn.addEventListener('click', toggleMicTest);
  }


  // --------------------------------------------------------------------------
  // Interactive Live Bookmarking During Recording
  // --------------------------------------------------------------------------
  bookmarkButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const type = btn.getAttribute('data-type') || 'Decision';
      const icon = btn.getAttribute('data-icon') || '📌';
      const elapsedSec = recordingStartTime ? Math.floor((Date.now() - recordingStartTime) / 1000) : 0;
      const mins = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
      const secs = String(elapsedSec % 60).padStart(2, '0');
      const timeStr = `[${mins}:${secs}]`;

      const bookmark = { time: timeStr, type, icon, timestamp: Date.now() };
      liveBookmarks.push(bookmark);

      if (liveBookmarksList) {
        const pill = document.createElement('span');
        pill.className = 'bookmark-pill-item';
        pill.innerHTML = `<strong>${timeStr}</strong> ${icon} ${type}`;
        liveBookmarksList.appendChild(pill);
        liveBookmarksList.scrollTop = liveBookmarksList.scrollHeight;
      }

      if (bookmarkCount) {
        bookmarkCount.textContent = `${liveBookmarks.length} tagged`;
      }

      // Haptic-like visual pulse on button
      btn.style.transform = 'scale(0.92)';
      setTimeout(() => { btn.style.transform = ''; }, 150);
    });
  });

  // --------------------------------------------------------------------------
  // Interactive Ask Aura Pre-Meeting Assistant
  // --------------------------------------------------------------------------
  if (prepAgendaBtn) {
    prepAgendaBtn.addEventListener('click', () => {
      meetingTitleInput.value = 'Sprint & Architecture Alignment Sync';
      meetingTitleInput.focus();
      auraPrepOutput.classList.remove('hidden');
      auraPrepOutput.innerHTML = `
        <strong>📋 15-Minute Recommended Flow:</strong><br>
        1. <strong>00:00 - 03:00</strong> — High-level blockers & status<br>
        2. <strong>03:00 - 10:00</strong> — Deep dive on key architecture decision<br>
        3. <strong>10:00 - 15:00</strong> — Action items, deadlines & ownership assignment
      `;
    });
  }

  if (prepIcebreakerBtn) {
    prepIcebreakerBtn.addEventListener('click', () => {
      const q = ICEBREAKERS[icebreakerIndex % ICEBREAKERS.length];
      icebreakerIndex++;
      auraPrepOutput.classList.remove('hidden');
      auraPrepOutput.innerHTML = `
        <strong>🎲 Meeting Kickoff Icebreaker:</strong><br>
        <span style="font-style: italic;">${q}</span>
      `;
    });
  }

  // --------------------------------------------------------------------------
  // Microphone Permission Status Check
  // --------------------------------------------------------------------------
  async function isMicAuthorized() {
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const perm = await navigator.permissions.query({ name: 'microphone' });
        return perm.state === 'granted';
      }
    } catch (e) {}

    return new Promise((resolve) => {
      chrome.storage.local.get(['micPermissionGranted'], (res) => {
        resolve(Boolean(res.micPermissionGranted));
      });
    });
  }

  async function checkMicPermissionStatus() {
    const isGranted = await isMicAuthorized();
    updateMicNotice(isGranted);
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const perm = await navigator.permissions.query({ name: 'microphone' });
        perm.onchange = async () => {
          const granted = await isMicAuthorized();
          updateMicNotice(granted);
        };
      }
    } catch (e) {}
  }

  function updateMicNotice(isGranted) {
    if (!micNoticeBox) return;
    if (isGranted) {
      micNoticeBox.classList.add('hidden');
    } else {
      micNoticeBox.classList.remove('hidden');
    }
  }

  if (openMicPermissionBtn) {
    openMicPermissionBtn.addEventListener('click', () => {
      chrome.tabs.create({ url: chrome.runtime.getURL('permission/permission.html') });
    });
  }

  checkMicPermissionStatus();

  // --------------------------------------------------------------------------
  // Check Backend Server Connectivity
  // --------------------------------------------------------------------------
  async function checkBackendHealth(url) {
    const cleanUrl = (url || 'http://localhost:8000').replace(/\/+$/, '');
    try {
      const res = await fetch(`${cleanUrl}/health`, { method: 'GET', cache: 'no-store' });
      if (res.ok) {
        if (serverDot) serverDot.style.background = '#10B981';
        if (serverStatusText) {
          serverStatusText.textContent = 'Online';
          serverStatusText.style.color = '#059669';
        }
      } else {
        throw new Error('Non-200 response');
      }
    } catch (e) {
      if (serverDot) serverDot.style.background = '#EF4444';
      if (serverStatusText) {
        serverStatusText.textContent = 'Offline';
        serverStatusText.style.color = '#DC2626';
      }
    }
  }

  chrome.storage.local.get(['backendUrl'], (res) => {
    if (res.backendUrl) backendUrlInput.value = res.backendUrl;
    dashboardLink.href = backendUrlInput.value;
    checkBackendHealth(backendUrlInput.value);
  });

  backendUrlInput.addEventListener('change', () => {
    chrome.storage.local.set({ backendUrl: backendUrlInput.value });
    dashboardLink.href = backendUrlInput.value;
    checkBackendHealth(backendUrlInput.value);
  });

  // Quick Template Chips
  document.querySelectorAll('.template-chips .chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const title = chip.getAttribute('data-title');
      if (title) {
        meetingTitleInput.value = title;
        meetingTitleInput.focus();
      }
    });
  });

  // --------------------------------------------------------------------------
  // Query Active Tab Metadata
  // --------------------------------------------------------------------------
  try {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (activeTab && activeTab.id) {
      chrome.tabs.sendMessage(activeTab.id, { action: 'GET_MEETING_METADATA' }, (response) => {
        if (chrome.runtime.lastError || !response) {
          if (activeTab.url && activeTab.url.includes('meet.google.com')) {
            updatePlatformBadge('Google Meet', true);
            meetingTitleInput.value = 'Google Meet Sync';
          } else if (activeTab.url && (activeTab.url.includes('teams.microsoft.com') || activeTab.url.includes('teams.live.com'))) {
            updatePlatformBadge('Microsoft Teams', true);
            meetingTitleInput.value = 'Microsoft Teams Sync';
          } else {
            updatePlatformBadge(activeTab.title ? 'Browser Tab' : 'Ready', false);
            if (activeTab.title) meetingTitleInput.value = activeTab.title.replace(/ - (Google Meet|Teams)/, '');
          }
          renderParticipantRow('Participant 1', '');
          renderParticipantRow('Participant 2', '');
          return;
        }

        if (response.platform) {
          updatePlatformBadge(response.platform, true);
        } else {
          updatePlatformBadge('Ready to Capture', false);
        }

        if (response.meetingTitle) meetingTitleInput.value = response.meetingTitle;
        if (response.participants && response.participants.length > 0) {
          participantList.innerHTML = '';
          response.participants.forEach((p) => renderParticipantRow(p.name, p.email || ''));
        } else {
          renderParticipantRow('Host', '');
          renderParticipantRow('Attendee', '');
        }
      });
    }
  } catch (err) {
    console.error('Error fetching tab info:', err);
    updatePlatformBadge('Ready to Capture', false);
  }

  function updatePlatformBadge(platformName, isConnected) {
    if (!platformPill || !platformLabel) return;
    if (platformName === 'Google Meet') {
      platformPill.className = 'platform-pill meet-active';
      platformLabel.innerHTML = '<strong>Google Meet</strong> Connected';
    } else if (platformName === 'Microsoft Teams') {
      platformPill.className = 'platform-pill teams-active';
      platformLabel.innerHTML = '<strong>Microsoft Teams</strong> Connected';
    } else {
      platformPill.className = 'platform-pill';
      platformLabel.textContent = isConnected ? `${platformName} Detected` : 'Ready to Capture Audio';
    }
  }

  // Restore current status from service worker
  chrome.runtime.sendMessage({ action: 'GET_STATUS' }, (status) => {
    if (status && status.isRecording) {
      setRecordingUI(true, status.startTime);
    } else {
      setRecordingUI(false);
    }
  });

  addParticipantBtn.addEventListener('click', () => {
    renderParticipantRow('', '');
  });

  function renderParticipantRow(name = '', email = '') {
    const row = document.createElement('div');
    row.className = 'participant-row';

    const avatar = document.createElement('div');
    avatar.className = 'participant-avatar';
    avatar.textContent = getInitials(name);
    // Click avatar to cycle accent colors
    const colors = [
      { bg: 'linear-gradient(135deg, #EDE9FE 0%, #E0E7FF 100%)', text: '#5B21B6' },
      { bg: 'linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)', text: '#065F46' },
      { bg: 'linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)', text: '#92400E' },
      { bg: 'linear-gradient(135deg, #FFF1F2 0%, #FFE4E6 100%)', text: '#9F1239' }
    ];
    let colorIdx = 0;
    avatar.addEventListener('click', () => {
      colorIdx = (colorIdx + 1) % colors.length;
      avatar.style.background = colors[colorIdx].bg;
      avatar.style.color = colors[colorIdx].text;
    });

    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.className = 'participant-name';
    nameInput.placeholder = 'Name';
    nameInput.value = name;
    nameInput.addEventListener('input', () => {
      avatar.textContent = getInitials(nameInput.value);
    });

    const emailInput = document.createElement('input');
    emailInput.type = 'email';
    emailInput.className = 'participant-email';
    emailInput.placeholder = 'Email (recap recipient)';
    emailInput.value = email;

    const removeBtn = document.createElement('button');
    removeBtn.className = 'participant-remove';
    removeBtn.innerHTML = '&times;';
    removeBtn.title = 'Remove attendee';
    removeBtn.addEventListener('click', () => {
      row.remove();
      updateAttendeeCount();
    });

    row.appendChild(avatar);
    row.appendChild(nameInput);
    row.appendChild(emailInput);
    row.appendChild(removeBtn);
    participantList.appendChild(row);
    updateAttendeeCount();
  }

  function getParticipants() {
    const rows = participantList.querySelectorAll('.participant-row');
    const participants = [];
    rows.forEach((row) => {
      const name = row.querySelector('.participant-name').value.trim();
      const email = row.querySelector('.participant-email').value.trim();
      if (name || email) {
        participants.push({ name: name || 'Participant', email: email || null });
      }
    });
    return participants;
  }

  function setRecordingUI(isRecording, startTime = Date.now()) {
    if (isRecording) {
      statusBadge.innerHTML = '<span class="status-dot"></span><span class="status-text">Recording</span>';
      statusBadge.className = 'badge badge-rec';
      recordBtn.innerHTML = '<span class="btn-icon">⏹</span> <span class="btn-text-main">Stop & Generate MoM</span>';
      recordBtn.className = 'btn btn-primary btn-recording';
      timerContainer.classList.remove('hidden');
      synthesisCard.classList.add('hidden');

      recordingStartTime = startTime;
      updateTimer();
      if (!timerInterval) {
        timerInterval = setInterval(updateTimer, 1000);
      }
    } else {
      statusBadge.innerHTML = '<span class="status-dot"></span><span class="status-text">Ready</span>';
      statusBadge.className = 'badge badge-idle';
      recordBtn.innerHTML = '<span class="btn-icon">⏺</span> <span class="btn-text-main">Start Recording</span>';
      recordBtn.className = 'btn btn-primary';
      timerContainer.classList.add('hidden');
      if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
      }
    }
  }

  function updateTimer() {
    if (!recordingStartTime) return;
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const secs = String(elapsed % 60).padStart(2, '0');
    recordingTimer.textContent = `${mins}:${secs}`;
  }

  function showAlert(msg, isError = false) {
    alertBox.textContent = msg;
    alertBox.className = `alert ${isError ? 'alert-error' : 'alert-success'}`;
    alertBox.classList.remove('hidden');
  }

  // --------------------------------------------------------------------------
  // Record Button Click Handler
  // --------------------------------------------------------------------------
  recordBtn.addEventListener('click', async () => {
    alertBox.classList.add('hidden');
    stopMicTest(); // Ensure test mic is closed before recording

    chrome.runtime.sendMessage({ action: 'GET_STATUS' }, async (status) => {
      if (status && status.isRecording) {
        // STOP RECORDING
        recordBtn.disabled = true;
        recordBtn.innerHTML = '<span class="btn-icon">⏳</span> <span class="btn-text-main">Transcribing with Gemini...</span>';
        statusBadge.innerHTML = '<span class="status-dot"></span><span class="status-text">Processing</span>';
        statusBadge.className = 'badge badge-processing';

        const finalElapsed = recordingStartTime ? Math.round((Date.now() - recordingStartTime) / 1000) : 10;

        chrome.runtime.sendMessage({ action: 'REQUEST_STOP' }, (res) => {
          recordBtn.disabled = false;
          setRecordingUI(false);

          if (res && res.success) {
            const mId = (res.res && res.res.result && res.res.result.meeting_id) || '';
            const bUrl = (backendUrlInput.value.trim() || 'http://localhost:8000').replace(/\/+$/, '');
            const notebookUrl = mId ? `${bUrl}/?meeting_id=${mId}#notebook` : `${bUrl}/#notebook`;

            // Display Interactive Synthesis Celebration Card
            synthesisCard.classList.remove('hidden');
            synDuration.textContent = `${finalElapsed}s duration`;
            const pCount = getParticipants().length;
            synAttendees.textContent = `${pCount} ${pCount === 1 ? 'attendee' : 'attendees'}`;
            synNotebookBtn.href = notebookUrl;

            // Copy Link Action
            copyMeetingLinkBtn.onclick = async () => {
              try {
                await navigator.clipboard.writeText(notebookUrl);
                copyLinkIcon.textContent = '✅';
                copyLinkText.textContent = 'Copied!';
                setTimeout(() => {
                  copyLinkIcon.textContent = '📋';
                  copyLinkText.textContent = 'Copy Link';
                }, 2000);
              } catch (e) {
                showAlert('Link copied: ' + notebookUrl, false);
              }
            };

            // Start New Meeting Action
            startNewMeetingBtn.onclick = () => {
              synthesisCard.classList.add('hidden');
              liveBookmarks = [];
              if (liveBookmarksList) liveBookmarksList.innerHTML = '';
              if (bookmarkCount) bookmarkCount.textContent = '0 tagged';
              meetingTitleInput.value = '';
              meetingTitleInput.focus();
            };

          } else {
            showAlert(`Processing failed: ${res ? res.error : 'Unknown error'}`, true);
          }
        });
      } else {
        // START RECORDING
        const micAllowed = await isMicAuthorized();
        if (!micAllowed) {
          chrome.tabs.create({ url: chrome.runtime.getURL('permission/permission.html') });
          showAlert('🎙️ Please click "Allow Microphone" on the tab that just opened to authorize audio mixing, then click Start Recording.', false);
          return;
        }

        recordBtn.disabled = true;
        recordBtn.innerHTML = '<span class="btn-icon">⏳</span> <span class="btn-text-main">Initializing audio stream...</span>';

        // Prepare metadata including bookmarks and focus mode
        const metadata = {
          meetingTitle: meetingTitleInput.value.trim() || 'Meeting Discussion',
          participants: getParticipants(),
          autoEmail: autoEmailToggle.checked,
          backendUrl: backendUrlInput.value.trim() || 'http://localhost:8000',
          source: 'web_extension',
          initialBookmarks: liveBookmarks
        };

        chrome.runtime.sendMessage({ action: 'REQUEST_START', metadata }, (res) => {
          recordBtn.disabled = false;
          if (res && res.success) {
            liveBookmarks = [];
            if (liveBookmarksList) liveBookmarksList.innerHTML = '';
            if (bookmarkCount) bookmarkCount.textContent = '0 tagged';
            setRecordingUI(true, Date.now());
          } else {
            showAlert(`Failed to start: ${res ? res.error : 'Audio capture failed'}`, true);
          }
        });
      }
    });
  });
});
