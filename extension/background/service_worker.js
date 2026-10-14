// Background Service Worker for Manifest V3

const OFFSCREEN_DOCUMENT_PATH = 'offscreen/offscreen.html';

async function ensureOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
    documentUrls: [chrome.runtime.getURL(OFFSCREEN_DOCUMENT_PATH)]
  });

  if (existingContexts.length === 0) {
    await chrome.offscreen.createDocument({
      url: OFFSCREEN_DOCUMENT_PATH,
      reasons: ['USER_MEDIA', 'AUDIO_PLAYBACK'],
      justification: 'Capturing and mixing meeting audio streams for AI transcription'
    });
  }
}

async function closeOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
    documentUrls: [chrome.runtime.getURL(OFFSCREEN_DOCUMENT_PATH)]
  });

  if (existingContexts.length > 0) {
    await chrome.offscreen.closeDocument();
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'REQUEST_START') {
    handleStartRecording(message.metadata)
      .then((res) => sendResponse({ success: true, res }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (message.action === 'REQUEST_STOP') {
    handleStopRecording()
      .then((res) => sendResponse({ success: true, res }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (message.action === 'GET_STATUS') {
    chrome.storage.local.get(['isRecording', 'meetingTitle', 'startTime'], (data) => {
      sendResponse(data);
    });
    return true;
  }
});

async function handleStartRecording(metadata) {
  // 1. Force close any stale offscreen document to ensure previous streams are terminated
  await closeOffscreenDocument();
  await ensureOffscreenDocument();

  // Find active tab
  const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!activeTab || !activeTab.id) {
    throw new Error('No active meeting tab found.');
  }

  // Get streamId for the active tab with friendly error detection
  let streamId;
  try {
    streamId = await chrome.tabCapture.getMediaStreamId({ targetTabId: activeTab.id });
  } catch (err) {
    if (err.message && err.message.includes('Cannot capture a tab with an active stream')) {
      await closeOffscreenDocument();
      throw new Error(
        'Chrome locked audio on this tab from a prior session. Refresh this meeting tab (press F5 or Ctrl+R) to release the stream, then click Start Recording.'
      );
    }
    throw err;
  }

  // Instruct offscreen document to begin capture
  const response = await chrome.runtime.sendMessage({
    action: 'START_RECORDING',
    streamId: streamId,
    metadata: {
      ...metadata,
      tabTitle: activeTab.title,
      tabUrl: activeTab.url
    }
  });

  if (response && response.status === 'RECORDING_STARTED') {
    await chrome.storage.local.set({
      isRecording: true,
      meetingTitle: metadata.meetingTitle || activeTab.title || 'Meeting',
      startTime: Date.now()
    });
    chrome.action.setBadgeText({ text: 'REC' });
    chrome.action.setBadgeBackgroundColor({ color: '#DC2626' }); // Red
    return response;
  } else {
    throw new Error(response ? response.message : 'Unknown offscreen error');
  }
}

async function handleStopRecording() {
  const response = await chrome.runtime.sendMessage({
    action: 'STOP_RECORDING'
  });

  await chrome.storage.local.set({ isRecording: false, startTime: null });
  chrome.action.setBadgeText({ text: '' });
  await closeOffscreenDocument();
  return response;
}
