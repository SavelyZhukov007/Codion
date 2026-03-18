// ============================
// CODION — main.js
// ============================

'use strict';

// --- Custom Cursor ---
const cursor = document.getElementById('cursor');
const cursorRing = document.getElementById('cursorRing');
let mouseX = 0, mouseY = 0;
let ringX = 0, ringY = 0;

document.addEventListener('mousemove', e => {
  mouseX = e.clientX;
  mouseY = e.clientY;
  cursor.style.left = mouseX + 'px';
  cursor.style.top = mouseY + 'px';
});

function animateCursorRing() {
  ringX += (mouseX - ringX) * 0.12;
  ringY += (mouseY - ringY) * 0.12;
  cursorRing.style.left = ringX + 'px';
  cursorRing.style.top = ringY + 'px';
  requestAnimationFrame(animateCursorRing);
}
animateCursorRing();

// Scale ring on hover over interactive elements
document.querySelectorAll('a, button, .project-card, .member-card, .nav__cta').forEach(el => {
  el.addEventListener('mouseenter', () => {
    cursorRing.style.width = '60px';
    cursorRing.style.height = '60px';
    cursorRing.style.borderColor = 'rgba(0,212,255,0.8)';
  });
  el.addEventListener('mouseleave', () => {
    cursorRing.style.width = '36px';
    cursorRing.style.height = '36px';
    cursorRing.style.borderColor = 'rgba(0,170,255,0.5)';
  });
});

// --- Particle Canvas ---
const canvas = document.getElementById('particleCanvas');
const ctx = canvas.getContext('2d');
let particles = [];
const PARTICLE_COUNT = 90;
const CONNECTION_DIST = 120;

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
resize();
window.addEventListener('resize', resize);

class Particle {
  constructor() { this.reset(); }
  reset() {
    this.x = Math.random() * canvas.width;
    this.y = Math.random() * canvas.height;
    this.vx = (Math.random() - 0.5) * 0.4;
    this.vy = (Math.random() - 0.5) * 0.4;
    this.r = Math.random() * 1.5 + 0.5;
    this.opacity = Math.random() * 0.5 + 0.2;
  }
  update() {
    this.x += this.vx;
    this.y += this.vy;
    if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
    if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
  }
  draw() {
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(0,170,255,${this.opacity})`;
    ctx.fill();
  }
}

for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(new Particle());

let heroMx = canvas.width / 2, heroMy = canvas.height / 2;
document.addEventListener('mousemove', e => { heroMx = e.clientX; heroMy = e.clientY; });

function drawParticles() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Mouse-influenced particle
  particles.forEach(p => {
    const dx = heroMx - p.x, dy = heroMy - p.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 180) {
      p.x -= dx * 0.002;
      p.y -= dy * 0.002;
    }
    p.update();
    p.draw();
  });

  // Connections
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x;
      const dy = particles[i].y - particles[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < CONNECTION_DIST) {
        const alpha = (1 - dist / CONNECTION_DIST) * 0.25;
        ctx.beginPath();
        ctx.moveTo(particles[i].x, particles[i].y);
        ctx.lineTo(particles[j].x, particles[j].y);
        ctx.strokeStyle = `rgba(0,170,255,${alpha})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }
    }
  }
  requestAnimationFrame(drawParticles);
}
drawParticles();

// --- Navbar Scroll ---
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 60);
  updateActiveNav();
});

function updateActiveNav() {
  const sections = document.querySelectorAll('section[id]');
  const links = document.querySelectorAll('.nav__links a');
  let current = '';
  sections.forEach(s => {
    if (window.scrollY >= s.offsetTop - 120) current = s.id;
  });
  links.forEach(a => {
    a.classList.remove('active');
    if (a.getAttribute('href') === '#' + current) a.classList.add('active');
  });
}

// --- Mobile menu ---
function toggleMenu() {
  const links = document.getElementById('navLinks');
  links.classList.toggle('open');
}

// --- Reveal on scroll ---
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, idx) => {
    if (entry.isIntersecting) {
      setTimeout(() => entry.target.classList.add('visible'), idx * 80);
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

// --- Counter animation ---
function animateCounter(el, target) {
  let current = 0;
  const step = target / 50;
  const timer = setInterval(() => {
    current += step;
    if (current >= target) { current = target; clearInterval(timer); }
    el.textContent = target > 2000
      ? Math.floor(current).toString()
      : Math.floor(current) + (el.dataset.suffix || '');
  }, 30);
}

const counterObserver = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      const strong = e.target.querySelector('strong');
      const raw = strong.textContent.replace(/[^0-9]/g, '');
      if (raw) animateCounter(strong, parseInt(raw, 10));
      counterObserver.unobserve(e.target);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('.about__stat').forEach(el => counterObserver.observe(el));

// --- Glitch title effect on hover ---
const heroTitle = document.querySelector('.hero__title');
if (heroTitle) {
  heroTitle.addEventListener('mouseenter', () => {
    heroTitle.style.animation = 'glitch 0.3s ease';
    setTimeout(() => heroTitle.style.animation = '', 400);
  });
}

// ============================
// CODION Insert API (used by insert.py preview & dynamic blocks loader)
// ============================
window.CodionInsert = {
  /**
   * Programmatically add a block to the page (used after insert.py writes HTML).
   * Call this from insert.py's preview iframe via postMessage or direct call.
   */
  addProjectCard({ title, tag, desc, tech = [], imgSrc = '', link = '#', isNew = true } = {}) {
    const grid = document.getElementById('projects-grid');
    if (!grid) return;
    const techHtml = tech.map(t => `<span>${t}</span>`).join('');
    const imgHtml = imgSrc
      ? `<div class="project-card__img-wrap"><img src="${imgSrc}" alt="${title}" class="project-card__img"/></div>`
      : '';
    const card = document.createElement('div');
    card.className = 'project-card reveal';
    if (isNew) card.dataset.added = 'true';
    card.innerHTML = `
      ${imgHtml}
      <div class="project-card__body">
        <p class="project-card__tag">// ${tag}</p>
        <h3 class="project-card__title">${title}</h3>
        <p class="project-card__desc">${desc}</p>
        <div class="project-card__tech">${techHtml}</div>
        <a href="${link}" class="project-card__link">Подробнее
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </a>
      </div>`;
    grid.appendChild(card);
    revealObserver.observe(card);
  },

  addNewsCard({ date = '', title = '', body = '', imgSrc = '' } = {}) {
    const container = document.getElementById('dynamic-blocks');
    if (!container) return;
    const imgHtml = imgSrc
      ? `<img src="${imgSrc}" alt="${title}" class="news-card__img"/>`
      : '';
    const card = document.createElement('div');
    card.className = 'news-card reveal';
    card.dataset.added = 'true';
    card.innerHTML = `
      ${imgHtml}
      <p class="news-card__date">// ${date}</p>
      <h3 class="news-card__title">${title}</h3>
      <p class="news-card__body">${body}</p>`;
    container.prepend(card);
    revealObserver.observe(card);
  },

  addTeamMember({ name = '', role = '', bio = '', skills = [], imgSrc = '', github = '#', telegram = '#' } = {}) {
    const grid = document.getElementById('team-grid');
    if (!grid) return;
    const skillsHtml = skills.map(s => `<span>${s}</span>`).join('');
    const imgContent = imgSrc
      ? `<img src="${imgSrc}" alt="${name}" class="member-card__img"/>`
      : `<div style="height:100%;background:linear-gradient(135deg,#0a1020,#0d1830);display:flex;align-items:center;justify-content:center;"><i class="fas fa-user" style="font-size:4rem;color:#1a3050;"></i></div>`;
    const card = document.createElement('div');
    card.className = 'member-card reveal';
    card.dataset.added = 'true';
    card.innerHTML = `
      <div class="member-card__img-wrap">${imgContent}</div>
      <div class="member-card__body">
        <p class="member-card__role">// ${role}</p>
        <h3 class="member-card__name">${name}</h3>
        <p class="member-card__bio">${bio}</p>
        <div class="member-card__skills">${skillsHtml}</div>
        <div class="member-card__socials">
          <a href="${github}" title="GitHub"><i class="fab fa-github"></i></a>
          <a href="${telegram}" title="Telegram"><i class="fab fa-telegram"></i></a>
        </div>
      </div>`;
    grid.appendChild(card);
    revealObserver.observe(card);
  }
};

console.log('%c⚡ CODION%c loaded', 'color:#00d4ff;font-size:20px;font-weight:900', 'color:#5b7498');
