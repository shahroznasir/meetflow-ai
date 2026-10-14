// Offscreen audio capture and dual-channel mixing for Manifest V3

let mediaRecorder = null;
let audioChunks = [];
let audioContext = null;
let micStream = null;
let tabStream = null;
let recordingMetadata = {};
let captureStartTime = 0;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'START_RECORDING') {
    startCapture(message.streamId, message.metadata)
      .then(() => sendResponse({ status: 'RECORDING_STARTED' }))
      .catch((err) => {
        console.error('Failed to start capture:', err.name, err.message, err);
        sendResponse({ status: 'ERROR', message: `${err.name || 'Error'}: ${err.message}` });
      });
    return true; // async
  }

  if (message.action === 'STOP_RECORDING') {
    stopCapture()
      .then((result) => sendResponse({ status: 'RECORDING_STOPPED', result }))
      .catch((err) => {
        console.error('Failed to stop capture:', err);
        sendResponse({ status: 'ERROR', message: err.message });
      });
    return true; // async
  }
});

async function startCapture(streamId, metadata) {
  recordingMetadata = metadata || {};
  audioChunks = [];
  captureStartTime = Date.now();

  // 1. Capture remote tab audio
  try {
    tabStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId
        }
      },
      video: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId
        }
      }
    });

    // Immediately stop video tracks to keep ONLY audio
    tabStream.getVideoTracks().forEach((track) => track.stop());
    console.log('Tab audio stream acquired.');
  } catch (tabErr) {
    console.warn('Tab capture with video constraint failed, attempting audio-only:', tabErr);
    try {
      tabStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          mandatory: {
            chromeMediaSource: 'tab',
            chromeMediaSourceId: streamId
          }
        }
      });
    } catch (tabErr2) {
      console.error('All tab capture attempts failed:', tabErr2);
      tabStream = null;
    }
  }

  // 2. Capture local host microphone
  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      },
      video: false
    });
    console.log('Local microphone stream acquired with enhancements.');
  } catch (micErr) {
    console.warn('Enhanced microphone capture failed, trying standard audio:', micErr);
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      console.log('Standard local microphone stream acquired.');
    } catch (stdErr) {
      console.error('All microphone acquisition attempts failed:', stdErr);
      micStream = null;
    }
  }

  if (!tabStream && !micStream) {
    throw new Error('Could not access either tab audio or microphone. Please check Chrome permissions.');
  }

  // 3. Configure Recording Stream
  let recordStream;

  if (tabStream && micStream) {
    // Both available: mix cleanly with Web Audio API
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === 'suspended') {
      await audioContext.resume();
    }

    const destination = audioContext.createMediaStreamDestination();
    destination.channelCount = 2;

    const tabSource = audioContext.createMediaStreamSource(tabStream);
    const micSource = audioContext.createMediaStreamSource(micStream);

    // Route tab to speakers so user can hear call attendees
    try {
      tabSource.connect(audioContext.destination);
    } catch (e) {
      console.warn('Speaker playback route warning:', e);
    }

    // Mix both channels with volume normalization
    const tabGain = audioContext.createGain();
    tabGain.gain.value = 1.0;
    tabSource.connect(tabGain);
    tabGain.connect(destination);

    const micGain = audioContext.createGain();
    micGain.gain.value = 1.2; // Slight boost for host speech clarity
    micSource.connect(micGain);
    micGain.connect(destination);

    recordStream = destination.stream;

    // Fix Chromium Bug 40094084: MediaStreamDestination requires an active consumer to pull buffers
    try {
      const pullSink = document.createElement('audio');
      pullSink.srcObject = destination.stream;
      pullSink.muted = true;
      pullSink.play().catch(() => {});
    } catch (e) {}

    console.log('Dual-channel audio mixed successfully. State:', audioContext.state);
  } else if (micStream) {
    // Host voice only (e.g. speaking alone in meeting): record hardware mic track directly
    recordStream = micStream;
    console.log('Recording microphone stream directly.');
  } else {
    // Tab only: also bridge tab to speakers so user can hear call
    try {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }
      const tabSource = audioContext.createMediaStreamSource(tabStream);
      tabSource.connect(audioContext.destination);
    } catch (e) {}
    recordStream = tabStream;
    console.log('Recording tab stream directly.');
  }

  // 4. Initialize MediaRecorder with cross-platform mimeType detection
  let options = {};
  if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
    options = { mimeType: 'audio/webm;codecs=opus' };
  } else if (MediaRecorder.isTypeSupported('audio/webm')) {
    options = { mimeType: 'audio/webm' };
  }

  mediaRecorder = new MediaRecorder(recordStream, options);

  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      audioChunks.push(event.data);
    }
  };

  // 1-second timeslices ensure continuous buffer flushing
  mediaRecorder.start(1000);
  console.log('Audio capture started successfully. Tab:', Boolean(tabStream), 'Mic:', Boolean(micStream));
}

function releaseAllTracks() {
  if (tabStream) {
    try { tabStream.getTracks().forEach((t) => t.stop()); } catch (e) {}
    tabStream = null;
  }
  if (micStream) {
    try { micStream.getTracks().forEach((t) => t.stop()); } catch (e) {}
    micStream = null;
  }
  if (audioContext && audioContext.state !== 'closed') {
    try { audioContext.close(); } catch (e) {}
    audioContext = null;
  }
}

// Ensure cleanup if offscreen window unloads
window.addEventListener('beforeunload', releaseAllTracks);
window.addEventListener('unload', releaseAllTracks);

async function stopCapture() {
  return new Promise((resolve, reject) => {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
      releaseAllTracks();
      return reject(new Error('MediaRecorder is not active.'));
    }

    mediaRecorder.onstop = async () => {
      try {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        console.log(`Audio recording stopped. Total size: ${audioBlob.size} bytes, chunks: ${audioChunks.length}`);

        // Clean up audio streams and context immediately
        releaseAllTracks();

        // Upload to Backend
        const uploadResult = await uploadMeetingPayload(audioBlob, recordingMetadata);
        resolve(uploadResult);
      } catch (err) {
        releaseAllTracks();
        reject(err);
      }
    };

    // Flush any pending audio data before stopping
    try {
      if (mediaRecorder.state === 'recording') {
        mediaRecorder.requestData();
      }
    } catch (e) {
      console.warn('requestData error:', e);
    }

    mediaRecorder.stop();
  });
}

async function uploadMeetingPayload(audioBlob, metadata) {
  const backendUrl = metadata.backendUrl || 'http://localhost:8000';
  const durationSeconds = Math.max(1, Math.round((Date.now() - captureStartTime) / 1000));

  const formData = new FormData();
  formData.append('audio_file', audioBlob, 'meeting_recording.webm');
  formData.append('meeting_title', metadata.meetingTitle || 'Meeting Discussion');
  formData.append('participants_json', JSON.stringify(metadata.participants || []));
  formData.append('source', metadata.source || 'browser_extension');
  formData.append('auto_email', metadata.autoEmail ? 'true' : 'false');
  formData.append('duration_seconds', String(durationSeconds));

  const response = await fetch(`${backendUrl}/api/v1/meetings/recordings`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Upload failed (${response.status}): ${errorText}`);
  }

  const result = await response.json();
  // Notify background worker
  chrome.runtime.sendMessage({
    action: 'PROCESSING_STARTED',
    meetingId: result.meeting_id,
    data: result
  });

  return result;
}
