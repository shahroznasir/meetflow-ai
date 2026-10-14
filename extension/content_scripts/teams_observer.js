// Microsoft Teams DOM observer to extract attendees and meeting title

function extractTeamsMetadata() {
  let meetingTitle = 'Microsoft Teams Meeting';
  const headerEl = document.querySelector('[data-tid="meeting-title"]') || document.querySelector('h1[role="heading"]');
  if (headerEl && headerEl.textContent.trim()) {
    meetingTitle = headerEl.textContent.trim();
  }

  const participants = new Set();
  // Query participant roster list items
  document.querySelectorAll('[data-tid="roster-participant"], [data-tid="participant-list-item"]').forEach((el) => {
    const nameEl = el.querySelector('[data-tid="roster-participant-name"]') || el;
    if (nameEl && nameEl.textContent.trim()) {
      participants.add(nameEl.textContent.trim());
    }
  });

  return {
    meetingTitle,
    platform: 'Microsoft Teams',
    participants: Array.from(participants).map((name) => ({ name, email: null }))
  };
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'GET_MEETING_METADATA') {
    sendResponse(extractTeamsMetadata());
  }
});
