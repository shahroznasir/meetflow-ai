// Handler for requesting microphone permission in a full browser tab

const grantBtn = document.getElementById('grantBtn');
const statusBox = document.getElementById('statusBox');

async function checkExistingPermission() {
  try {
    const perm = await navigator.permissions.query({ name: 'microphone' });
    if (perm.state === 'granted') {
      showSuccess(true);
    }
    perm.onchange = () => {
      if (perm.state === 'granted') {
        showSuccess();
      }
    };
  } catch (err) {
    // Some browsers might not support permissions.query for microphone
  }
}

function showSuccess(alreadyGranted = false) {
  grantBtn.style.display = 'none';
  statusBox.className = 'status-box status-success';
  statusBox.style.display = 'block';
  statusBox.innerHTML = `
    <strong>✅ Microphone Access ${alreadyGranted ? 'Already Active' : 'Granted'}!</strong>
    <div style="margin-top: 8px; font-size: 13px; color: #047857;">
      Your extension is now configured. You can close this tab and return to your meeting.
    </div>
    <button id="closeTabBtn" style="margin-top: 14px; background: #059669; border: none; color: white; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600;">Close Tab</button>
  `;

  chrome.storage.local.set({ micPermissionGranted: true });

  const closeBtn = document.getElementById('closeTabBtn');
  if (closeBtn) {
    closeBtn.onclick = () => window.close();
  }

  // Auto close tab after 3 seconds if freshly granted
  if (!alreadyGranted) {
    setTimeout(() => {
      window.close();
    }, 3000);
  }
}

function showError(msg) {
  statusBox.className = 'status-box status-error';
  statusBox.style.display = 'block';
  statusBox.innerHTML = `
    <strong>⚠️ Permission Needed</strong>
    <div style="margin-top: 6px; font-size: 13px;">
      ${msg}
    </div>
    <div style="margin-top: 10px; font-size: 12px; color: #b91c1c;">
      If Chrome blocked it: click the icon on the left side of the address bar above, set Microphone to <strong>"Allow"</strong>, and reload this page.
    </div>
  `;
  grantBtn.disabled = false;
  grantBtn.innerHTML = '<span>Try Again</span>';
}

grantBtn.addEventListener('click', async () => {
  grantBtn.disabled = true;
  grantBtn.innerHTML = '<span>Requesting...</span>';
  statusBox.style.display = 'none';

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // Immediately stop tracks after receiving permission
    stream.getTracks().forEach((track) => track.stop());
    showSuccess();
  } catch (err) {
    console.error('Microphone request error:', err);
    showError(err.message || 'Microphone access was denied or cancelled.');
  }
});

// Check status on page load
checkExistingPermission();
