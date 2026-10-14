// Google Meet DOM observer to extract attendees, meeting code, and meeting title

function extractMeetMetadata() {
  const meetingCode = window.location.pathname.replace(/^\//, '');
  
  // Extract meeting code or title
  let meetingTitle = 'Google Meet';
  const titleEl = document.querySelector('[data-meeting-title]') || document.querySelector('div[jsname="r4nke"]');
  if (titleEl && titleEl.textContent.trim()) {
    meetingTitle = titleEl.textContent.trim();
  } else if (meetingCode) {
    meetingTitle = `Google Meet (${meetingCode})`;
  }

  // Extract participants from attendee list or tiles
  const participants = new Set();

  function cleanName(raw) {
    if (!raw) return null;
    const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    const filtered = lines.filter(l => !/^(more_vert|visual_effects|frame_person|mic|videocam|devices|Reframe|Backgrounds|Turn on|Turn off)/i.test(l));
    if (filtered.length > 0) return filtered[0];
    const match = raw.match(/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)/);
    return match ? match[1] : raw.trim().slice(0, 30);
  }

  // 1. Direct self-name attribute
  document.querySelectorAll('[data-self-name]').forEach((el) => {
    const name = el.getAttribute('data-self-name');
    if (name && name.trim()) participants.add(name.trim());
  });

  // 2. Speaker tile name labels (Google Meet uses specific classes for participant names)
  document.querySelectorAll('div[data-sender-name], span.notranslate.zWGUib, span.dwSJ2e, div.c3bvEb').forEach((el) => {
    const text = el.getAttribute('data-sender-name') || el.textContent;
    const cleaned = cleanName(text);
    if (cleaned && cleaned.length > 2) participants.add(cleaned);
  });

  return {
    meetingTitle,
    meetingCode,
    platform: 'Google Meet',
    participants: Array.from(participants).map((name) => ({ name, email: null }))
  };
}

// Listen for requests from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'GET_MEETING_METADATA') {
    sendResponse(extractMeetMetadata());
  }
});
