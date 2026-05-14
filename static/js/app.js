// ZYNARA – frontend logic

const audio = document.getElementById('audioEl');
const player = document.getElementById('player');
const playerPlayBtn = document.getElementById('playerPlayBtn');
const playerPlayIcon = document.getElementById('playerPlayIcon');
const playerPauseIcon = document.getElementById('playerPauseIcon');
const playerTitle = document.getElementById('playerTitle');
const playerArtist = document.getElementById('playerArtist');
const progressBar = document.getElementById('progressBar');
const playerCurrent = document.getElementById('playerCurrent');
const playerDuration = document.getElementById('playerDuration');
const volumeBar = document.getElementById('volumeBar');
const purchaseModal = document.getElementById('purchaseModal');
const modalClose = document.getElementById('modalClose');

let currentTrack = null;
let purchaseTarget = null; // { id, name, price, type: 'song'|'album' }
let unlocked = JSON.parse(localStorage.getItem('zynara_unlocked') || '[]');
// tokens: { songId -> token, 'album' -> token }
let tokens = JSON.parse(localStorage.getItem('zynara_tokens') || '{}');
let pollInterval = null;
let timerInterval = null;
let currentReferenceId = null;
let albumData = null;

// ── Load album data ────────────────────────────────────────────────
fetch('/api/album')
  .then(r => r.json())
  .then(data => {
    albumData = data;
    renderAlbum(data);
  });

function renderAlbum(data) {
  if (data.demo_mode) {
    document.getElementById('demoBanner').classList.remove('hidden');
  }
  document.getElementById('albumTitle').textContent = data.title;
  document.getElementById('artistName').textContent = data.artist;
  document.getElementById('albumDesc').textContent = data.description || '';
  document.getElementById('songCount').textContent = `${data.songs.length} songs`;
  document.getElementById('albumYear').textContent = data.year || '';
  document.getElementById('albumPrice').textContent = data.album_price_display;
  document.getElementById('footerYear').textContent = new Date().getFullYear();

  const coverEl = document.getElementById('albumCoverImg');
  if (data.cover) coverEl.src = `/static/img/${data.cover}`;

  document.getElementById('buyAlbumBtn').addEventListener('click', () => {
    openPurchase({ id: 'album', name: `${data.title} (Full Album)`, price: data.album_price_display, type: 'album' });
  });

  renderTracks(data.songs);
}

function isUnlocked(songId) {
  return unlocked.includes('album') || unlocked.includes(String(songId));
}

function renderTracks(songs) {
  const list = document.getElementById('trackList');
  list.innerHTML = '';
  songs.forEach((song, i) => {
    const locked = !isUnlocked(song.id);
    const item = document.createElement('div');
    item.className = `track-item${locked ? ' locked' : ''}`;
    item.dataset.id = song.id;

    item.innerHTML = `
      <div class="track-num">
        <span class="num-text">${i + 1}</span>
        <span class="play-icon">${locked ? '🔒' : '▶'}</span>
      </div>
      <img class="track-cover" src="/static/img/${song.cover || albumData.cover || 'placeholder.svg'}"
           alt="" onerror="this.src='/static/img/placeholder.svg'" />
      <div class="track-info">
        <div class="track-name">${song.title}</div>
        <div class="track-artist">${song.artist || albumData.artist}</div>
      </div>
      <span class="track-duration">${song.duration || ''}</span>
      <div class="track-actions">
        ${locked
          ? `<button class="btn-buy-song" data-id="${song.id}" data-name="${song.title}" data-price="${song.price_display}">
               Buy ${song.price_display}
             </button><span class="lock-icon">🔒</span>`
          : `<span class="unlocked-badge">✓ Unlocked</span>`
        }
      </div>`;

    item.addEventListener('click', (e) => {
      if (e.target.classList.contains('btn-buy-song')) {
        openPurchase({ id: song.id, name: song.title, price: song.price_display, type: 'song' });
        return;
      }
      if (!isUnlocked(song.id)) {
        openPurchase({ id: song.id, name: song.title, price: song.price_display, type: 'song' });
        return;
      }
      playTrack(song);
    });

    list.appendChild(item);
  });
}

// ── Audio Player ───────────────────────────────────────────────────
function streamUrl(songId) {
  // Use album token first, then song-specific token
  const tok = tokens['album'] || tokens[String(songId)] || '';
  return `/api/stream/${songId}?t=${encodeURIComponent(tok)}`;
}

function playTrack(song) {
  if (currentTrack && currentTrack.id === song.id) {
    togglePlay();
    return;
  }
  currentTrack = song;
  audio.src = streamUrl(song.id);
  audio.volume = volumeBar.value / 100;
  audio.play();
  player.classList.remove('hidden');
  playerTitle.textContent = song.title;
  playerArtist.textContent = song.artist || albumData.artist;
  updatePlayingState(true);
  highlightTrack(song.id);
}

function togglePlay() {
  if (audio.paused) {
    audio.play();
    updatePlayingState(true);
  } else {
    audio.pause();
    updatePlayingState(false);
  }
}

function updatePlayingState(playing) {
  playerPlayIcon.classList.toggle('hidden', playing);
  playerPauseIcon.classList.toggle('hidden', !playing);
  document.querySelectorAll('.track-item').forEach(el => {
    const isThis = currentTrack && el.dataset.id == currentTrack.id;
    el.classList.toggle('playing', isThis && playing);
    el.classList.toggle('paused', isThis && !playing);
  });
}

function highlightTrack(id) {
  document.querySelectorAll('.track-item').forEach(el => {
    el.classList.toggle('playing', el.dataset.id == id);
  });
}

playerPlayBtn.addEventListener('click', togglePlay);

audio.addEventListener('timeupdate', () => {
  if (!audio.duration) return;
  const pct = (audio.currentTime / audio.duration) * 100;
  progressBar.value = pct;
  playerCurrent.textContent = fmt(audio.currentTime);
  playerDuration.textContent = fmt(audio.duration);
});

audio.addEventListener('ended', () => {
  updatePlayingState(false);
  const songs = albumData ? albumData.songs.filter(s => isUnlocked(s.id)) : [];
  if (!currentTrack || !songs.length) return;
  const idx = songs.findIndex(s => s.id == currentTrack.id);
  if (idx >= 0 && idx < songs.length - 1) playTrack(songs[idx + 1]);
});

progressBar.addEventListener('input', () => {
  if (audio.duration) audio.currentTime = (progressBar.value / 100) * audio.duration;
});
volumeBar.addEventListener('input', () => { audio.volume = volumeBar.value / 100; });

function fmt(s) {
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60).toString().padStart(2, '0');
  return `${m}:${ss}`;
}

// ── Purchase Modal ─────────────────────────────────────────────────
function openPurchase(target) {
  purchaseTarget = target;
  document.getElementById('modalItemName').textContent = target.name;
  document.getElementById('modalItemPrice').textContent = target.price;
  showStep('phone');
  document.getElementById('phoneInput').value = '';
  document.getElementById('phoneError').classList.add('hidden');
  purchaseModal.classList.remove('hidden');
}

modalClose.addEventListener('click', closePurchaseModal);
purchaseModal.addEventListener('click', e => { if (e.target === purchaseModal) closePurchaseModal(); });

function closePurchaseModal() {
  purchaseModal.classList.add('hidden');
  clearInterval(pollInterval);
  clearInterval(timerInterval);
  currentReferenceId = null;
}

function showStep(name) {
  ['stepPhone', 'stepWaiting', 'stepSuccess', 'stepFailed'].forEach(id => {
    document.getElementById(id).classList.toggle('hidden', id !== `step${capitalize(name)}`);
  });
}
function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

document.getElementById('confirmPayBtn').addEventListener('click', initiatePayment);
document.getElementById('retryBtn').addEventListener('click', () => showStep('phone'));
document.getElementById('playNowBtn').addEventListener('click', () => {
  closePurchaseModal();
  if (purchaseTarget && albumData) {
    if (purchaseTarget.type === 'album') {
      const first = albumData.songs[0];
      if (first) playTrack(first);
    } else {
      const song = albumData.songs.find(s => s.id == purchaseTarget.id);
      if (song) playTrack(song);
    }
  }
});

async function initiatePayment() {
  const phone = document.getElementById('phoneInput').value.trim();
  const errEl = document.getElementById('phoneError');
  errEl.classList.add('hidden');

  if (!phone || phone.length < 9) {
    errEl.textContent = 'Please enter a valid phone number.';
    errEl.classList.remove('hidden');
    return;
  }

  const btn = document.getElementById('confirmPayBtn');
  btn.disabled = true;
  document.getElementById('payBtnText').classList.add('hidden');
  document.getElementById('payBtnSpinner').classList.remove('hidden');

  try {
    const res = await fetch('/api/purchase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone,
        item_id: purchaseTarget.id,
        item_type: purchaseTarget.type,
        item_name: purchaseTarget.name
      })
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Payment request failed');
    }
    currentReferenceId = data.reference_id;
    document.getElementById('waitingPhone').textContent = phone;
    showStep('waiting');
    startPolling(data.reference_id);
  } catch (err) {
    errEl.textContent = err.message || 'Something went wrong. Please try again.';
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    document.getElementById('payBtnText').classList.remove('hidden');
    document.getElementById('payBtnSpinner').classList.add('hidden');
  }
}

function startPolling(referenceId) {
  let elapsed = 0;
  const TIMEOUT = 120;
  const timerBar = document.getElementById('timerBar');
  const timerText = document.getElementById('timerText');
  const statusEl = document.getElementById('waitingStatus');

  timerBar.style.width = '100%';
  timerText.textContent = `${TIMEOUT}s`;

  timerInterval = setInterval(() => {
    elapsed++;
    const pct = Math.max(0, ((TIMEOUT - elapsed) / TIMEOUT) * 100);
    timerBar.style.width = pct + '%';
    timerText.textContent = `${TIMEOUT - elapsed}s`;
    if (elapsed >= TIMEOUT) {
      clearInterval(timerInterval);
      clearInterval(pollInterval);
      document.getElementById('failDesc').textContent = 'The request timed out. Please try again.';
      showStep('failed');
    }
  }, 1000);

  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/verify/${referenceId}`);
      const data = await res.json();
      statusEl.textContent = data.message || 'Checking...';

      if (data.status === 'SUCCESSFUL') {
        clearInterval(pollInterval);
        clearInterval(timerInterval);
        markUnlocked(purchaseTarget, data.token);
        showStep('success');
      } else if (data.status === 'FAILED') {
        clearInterval(pollInterval);
        clearInterval(timerInterval);
        document.getElementById('failDesc').textContent = data.message || 'Payment was declined.';
        showStep('failed');
      }
    } catch (e) { /* keep polling */ }
  }, 4000);
}

function markUnlocked(target, token) {
  if (target.type === 'album') {
    unlocked = ['album'];
    if (token) tokens['album'] = token;
  } else {
    if (!unlocked.includes(String(target.id))) {
      unlocked.push(String(target.id));
    }
    if (token) tokens[String(target.id)] = token;
  }
  localStorage.setItem('zynara_unlocked', JSON.stringify(unlocked));
  localStorage.setItem('zynara_tokens', JSON.stringify(tokens));
  if (albumData) renderTracks(albumData.songs);
}
