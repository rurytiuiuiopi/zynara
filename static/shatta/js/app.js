/* SHATTA TUESDAY MARKET — Frontend JS */

// ── Nav toggle (mobile) ───────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('navToggle');
  const links  = document.getElementById('navLinks');
  if (toggle && links) {
    toggle.addEventListener('click', () => links.classList.toggle('open'));
    document.addEventListener('click', e => {
      if (!toggle.contains(e.target) && !links.contains(e.target)) {
        links.classList.remove('open');
      }
    });
  }

  // Auto-dismiss flash alerts after 5s
  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });

  // Set today's min date on promotion date inputs
  const dateInput = document.querySelector('input[name="promotion_date"]');
  if (dateInput) {
    dateInput.min = new Date().toISOString().split('T')[0];
  }
});

// ── Password toggle ───────────────────────────────────────
function togglePassword(id) {
  const input = document.getElementById(id);
  if (!input) return;
  input.type = input.type === 'password' ? 'text' : 'password';
}

// ── Toast notification ────────────────────────────────────
function showToast(msg, duration = 3000) {
  const toast = document.createElement('div');
  toast.className = 'toast-popup';
  toast.textContent = msg;
  document.body.appendChild(toast);
  requestAnimationFrame(() => {
    requestAnimationFrame(() => toast.classList.add('show'));
  });
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 400);
  }, duration);
}

// ── Copy to clipboard helper ──────────────────────────────
function copyText(text, successMsg = 'Copied!') {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => showToast(successMsg));
  } else {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    showToast(successMsg);
  }
}

// ── Animate numbers on stats bar ─────────────────────────
function animateNumbers() {
  document.querySelectorAll('.stat-number').forEach(el => {
    const target = parseInt(el.textContent);
    if (isNaN(target) || target === 0) return;
    let current = 0;
    const step  = Math.ceil(target / 40);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 25);
  });
}

// Trigger number animation when stats bar enters viewport
const statsBar = document.querySelector('.stats-bar');
if (statsBar) {
  const obs = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) { animateNumbers(); obs.disconnect(); }
  }, { threshold: 0.3 });
  obs.observe(statsBar);
}

// ── Smooth scroll for anchor links ───────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});
