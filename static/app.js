let currentJobId = null;
let activePolls = {};
let currentTranscript = null;
let richPointWords = [];
let activeHistoryId = null;

document.addEventListener('DOMContentLoaded', () => {
    fetchHistory();
});

// ---------------------------------------------------------------------------
// Sidebar / History
// ---------------------------------------------------------------------------

function fetchHistory() {
    fetch('/api/history')
        .then(r => r.json())
        .then(items => renderSidebar(items))
        .catch(() => {});
}

function renderSidebar(items) {
    const list = document.getElementById('sidebar-list');
    if (!items || items.length === 0) {
        list.innerHTML = '<p class="sidebar-empty">No videos analyzed yet</p>';
        return;
    }
    list.innerHTML = '';
    items.forEach(item => {
        const el = document.createElement('div');
        el.className = 'sidebar-item' + (item.job_id === activeHistoryId ? ' active' : '');
        el.onclick = () => loadFromHistory(item.job_id);
        const videoId = extractVideoId(item.url);
        let timeStr = '';
        if (item.created_at) {
            const d = new Date(item.created_at * 1000);
            timeStr = d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
        }
        el.innerHTML = `
            <div class="sidebar-url" title="${esc(item.url)}">${esc(videoId || item.url)}</div>
            <div class="sidebar-stats">
                <span>${item.rich_points_count} RP</span>
                <span>${item.topics_count} topics</span>
            </div>
            ${timeStr ? `<div class="sidebar-time">${timeStr}</div>` : ''}
        `;
        list.appendChild(el);
    });
}

function extractVideoId(url) {
    const m = url.match(/(?:v=|youtu\.be\/)([^&?\s]+)/);
    return m ? m[1] : null;
}

function loadFromHistory(jobId) {
    activeHistoryId = jobId;
    fetch(`/api/status/${jobId}`)
        .then(r => r.json())
        .then(job => {
            if (job.status === 'done') {
                document.getElementById('welcome-section').classList.add('hidden');
                document.getElementById('status-section').classList.add('hidden');
                document.getElementById('error-section').classList.add('hidden');
                renderResults(job);
                fetchHistory();
            }
        });
}

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------

function startAnalysis() {
    const url = document.getElementById('url-input').value.trim();
    if (!url) return;
    document.getElementById('url-input').value = '';
    document.getElementById('results-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');
    document.getElementById('welcome-section').classList.add('hidden');
    document.getElementById('status-section').classList.remove('hidden');
    activeHistoryId = null;
    resetSteps();

    fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) { showError(data.error); return; }
        currentJobId = data.job_id;
        addProcessingToSidebar(data.job_id, url);
        activePolls[data.job_id] = setInterval(() => pollJob(data.job_id), 1500);
    })
    .catch(err => showError(err.message));
}

function addProcessingToSidebar(jobId, url) {
    const list = document.getElementById('sidebar-list');
    const empty = list.querySelector('.sidebar-empty');
    if (empty) empty.remove();
    const el = document.createElement('div');
    el.className = 'sidebar-item processing active';
    el.id = `sidebar-${jobId}`;
    const videoId = extractVideoId(url);
    el.innerHTML = `
        <div class="sidebar-url" title="${esc(url)}">${esc(videoId || url)}</div>
        <div class="sidebar-stats"><span>analyzing...</span></div>
    `;
    el.onclick = () => {
        currentJobId = jobId;
        activeHistoryId = null;
        document.querySelectorAll('.sidebar-item').forEach(s => s.classList.remove('active'));
        el.classList.add('active');
    };
    list.prepend(el);
}

function pollJob(jobId) {
    fetch(`/api/status/${jobId}`)
        .then(r => r.json())
        .then(job => {
            if (jobId === currentJobId) {
                document.getElementById('status-text').textContent = job.message;
                updateSteps(job.status);
            }
            if (job.status === 'done') {
                clearInterval(activePolls[jobId]);
                delete activePolls[jobId];
                if (jobId === currentJobId) {
                    document.getElementById('status-section').classList.add('hidden');
                    activeHistoryId = jobId;
                    renderResults(job);
                }
                fetchHistory();
            } else if (job.status === 'error') {
                clearInterval(activePolls[jobId]);
                delete activePolls[jobId];
                if (jobId === currentJobId) {
                    document.getElementById('status-section').classList.add('hidden');
                    showError(job.message);
                }
                const el = document.getElementById(`sidebar-${jobId}`);
                if (el) el.remove();
            }
        });
}

function resetSteps() {
    ['step-fetch', 'step-split', 'step-scan', 'step-l1', 'step-l2', 'step-topics'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.remove('active', 'done');
    });
}

function updateSteps(status) {
    const order = ['fetching', 'splitting', 'scanning', 'level1', 'level2', 'topics', 'done'];
    const stepMap = {
        fetching: 'step-fetch',
        splitting: 'step-split',
        scanning: 'step-scan',
        level1: 'step-l1',
        level2: 'step-l2',
        topics: 'step-topics'
    };
    const currentIdx = order.indexOf(status);
    Object.entries(stepMap).forEach(([key, id]) => {
        const el = document.getElementById(id);
        if (!el) return;
        const idx = order.indexOf(key);
        el.classList.remove('active', 'done');
        if (idx < currentIdx) el.classList.add('done');
        else if (idx === currentIdx) el.classList.add('active');
    });
    if (status === 'done') {
        Object.values(stepMap).forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            el.classList.remove('active');
            el.classList.add('done');
        });
    }
}

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

function switchTab(btn) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
}

// ---------------------------------------------------------------------------
// Render all results
// ---------------------------------------------------------------------------

function renderResults(job) {
    const section = document.getElementById('results-section');

    const urlBar = document.getElementById('video-url-bar');
    const videoUrl = job.url || '';
    urlBar.innerHTML = videoUrl ? `<a href="${esc(videoUrl)}" target="_blank">${esc(videoUrl)}</a>` : '';

    // Rich points (B-series)
    const results = job.results || [];
    richPointWords = results.map(rp => rp.word.toLowerCase());
    renderRichPoints(results);

    // Cultural Topics (D1 + D2)
    renderTopics(job.d1 || {}, job.d2 || {});

    // Transcript
    renderTranscript(job.transcript || [], job.word_count || 0);

    // Overview
    renderOverview(job);

    document.getElementById('welcome-section').classList.add('hidden');
    section.classList.remove('hidden');

    const overviewBtn = document.querySelector('[data-tab="tab-overview"]');
    if (overviewBtn) switchTab(overviewBtn);
}

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------

function renderOverview(job) {
    const grid = document.getElementById('overview-grid');
    const rp = (job.results || []).length;
    const topicCount = ((job.d1 || {}).topics || []).length;
    const articleCount = ((job.d2 || {}).articles || []).length;

    grid.innerHTML = `
        ${overviewCard('Rich Points', rp, 'cultural terms discovered')}
        ${overviewCard('Cultural Topics', topicCount, 'topics detected (D1)')}
        ${overviewCard('Deep-Dive Articles', articleCount, 'topic explainers generated (D2)')}
        ${overviewCard('Transcript', (job.word_count || 0).toLocaleString(), 'words')}
    `;
}

function overviewCard(title, num, sub) {
    return `<div class="overview-card"><h3>${esc(title)}</h3><div class="overview-number">${num}</div><div class="overview-sub">${esc(sub)}</div></div>`;
}

// ---------------------------------------------------------------------------
// Rich Points tab
// ---------------------------------------------------------------------------

function renderRichPoints(results) {
    const meta = document.getElementById('results-meta');
    const list = document.getElementById('results-list');
    meta.textContent = `${results.length} rich point(s) found`;
    list.innerHTML = '';
    if (results.length === 0) {
        list.innerHTML = '<p style="color:#888;text-align:center;padding:40px 0;">No rich points found.</p>';
        return;
    }
    results.forEach((rp, i) => {
        const card = document.createElement('div');
        card.className = 'rp-card' + (i === 0 ? ' open' : '');
        card.innerHTML = buildRpCard(rp);
        card.querySelector('.rp-card-header').addEventListener('click', () => card.classList.toggle('open'));
        list.appendChild(card);
    });
}

function buildRpCard(rp) {
    const ts = rp.timestamp_seconds || 0;
    const timeStr = fmtTime(ts);
    const related = (rp.related_rich_points || []).map(r => `<span class="rp-tag">${esc(r)}</span>`).join('');
    return `
        <div class="rp-card-header">
            <div><span class="rp-word">${esc(rp.word)}</span><span class="rp-meta">${esc(rp.type || '')} · ${esc(rp.pos || '')} · ${esc(rp.sense_tag || '')}</span></div>
            <span class="rp-toggle">&#x25BC;</span>
        </div>
        <div class="rp-card-body">
            ${field('Definition', rp.definition)}
            ${field('Meaning in this video', rp.context_meaning)}
            ${rp.transcript_quote ? `<div class="rp-section"><div class="rp-section-label">From the transcript <span class="rp-timestamp">${timeStr}</span></div><div class="rp-section-content rp-quote">${esc(rp.transcript_quote)}</div></div>` : ''}
            <div class="rp-divider"></div>
            ${field('Why is this a rich point?', rp.why_rich_point)}
            ${field('What if you use it wrong?', rp.misuse_consequence)}
            ${field('Origin', rp.origin_story)}
            ${field('When to use / not use', rp.when_to_use)}
            ${related ? `<div class="rp-section"><div class="rp-section-label">Related rich points</div><div class="rp-tags">${related}</div></div>` : ''}
            ${field('How to say it as an outsider', rp.outsider_rephrase)}
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Cultural Topics tab (D1 + D2)
// ---------------------------------------------------------------------------

function renderTopics(d1, d2) {
    const meta = document.getElementById('topics-meta');
    const list = document.getElementById('topics-list');

    const articles = d2.articles || [];
    const articleMap = {};
    articles.forEach(a => {
        const key = (a.topic_title || '').toLowerCase();
        articleMap[key] = a;
    });

    const topics = d1.topics || [];

    meta.textContent = `${topics.length} topic(s), ${articles.length} article(s)`;
    list.innerHTML = '';

    if (topics.length === 0) {
        list.innerHTML = '<p style="color:#888;text-align:center;padding:40px 0;">No cultural topics detected.</p>';
        return;
    }

    topics.forEach((topic, i) => {
        const article = articleMap[(topic.title || '').toLowerCase()] || {};
        const card = document.createElement('div');
        card.className = 'stamp-card' + (i === 0 ? ' open' : '');
        card.innerHTML = buildTopicCard(topic, article);
        card.querySelector('.stamp-card-header').addEventListener('click', () => card.classList.toggle('open'));
        list.appendChild(card);
    });
}

function buildTopicCard(topic, article) {
    const sections = article.sections || {};
    const sectionsHtml = Object.entries(sections).map(([key, val]) => `
        <div class="stamp-section">
            <h4>${esc(key.replace(/_/g, ' '))}</h4>
            <p>${esc(val)}</p>
        </div>
    `).join('');

    const tr = topic.time_range || [0, 0];
    const startStr = fmtTime((tr[0] || 0) / 1000);
    const endStr = fmtTime((tr[1] || 0) / 1000);
    const conf = typeof topic.confidence === 'number' ? topic.confidence.toFixed(2) : '';

    const quotesHtml = (topic.evidence_quotes || []).map(q =>
        `<div class="rp-section-content rp-quote">${esc(q)}</div>`
    ).join('');

    return `
        <div class="stamp-card-header">
            <div>
                <span class="stamp-name">${esc(topic.title)}</span>
                <span class="stamp-category">${startStr}–${endStr}${conf ? ' · conf ' + conf : ''}</span>
            </div>
            <span class="rp-toggle">&#x25BC;</span>
        </div>
        <div class="stamp-card-body">
            ${topic.short ? `<div class="rp-section"><div class="rp-section-label">In short</div><div class="rp-section-content">${esc(topic.short)}</div></div>` : ''}
            ${quotesHtml ? `<div class="rp-section"><div class="rp-section-label">Evidence quotes</div>${quotesHtml}</div>` : ''}
            ${article.tl_dr ? `<div class="rp-section"><div class="rp-section-label">TL;DR</div><div class="stamp-tldr">${esc(article.tl_dr)}</div></div>` : ''}
            ${sectionsHtml}
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Transcript tab
// ---------------------------------------------------------------------------

function renderTranscript(segments, wordCount) {
    const body = document.getElementById('transcript-body');
    const meta = document.getElementById('transcript-meta');
    meta.textContent = `${wordCount.toLocaleString()} words · ${segments.length} sentences`;

    if (!segments || segments.length === 0) {
        body.innerHTML = '<p style="color:#555;">No transcript available.</p>';
        return;
    }

    let html = '';
    segments.forEach(seg => {
        const ts = fmtTime(seg.start || 0);
        const highlighted = highlightRichPoints(seg.text);
        html += `<div class="transcript-line"><span class="transcript-ts">${ts}</span>${highlighted}</div>`;
    });
    body.innerHTML = html;
}

function highlightRichPoints(text) {
    if (richPointWords.length === 0) return esc(text);
    const sorted = [...richPointWords].sort((a, b) => b.length - a.length);
    const escaped = sorted.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const pattern = new RegExp('\\b(' + escaped.join('|') + ')\\b', 'gi');
    let result = '';
    let lastIndex = 0;
    let match;
    pattern.lastIndex = 0;
    while ((match = pattern.exec(text)) !== null) {
        result += esc(text.slice(lastIndex, match.index));
        result += `<span class="highlight">${esc(match[0])}</span>`;
        lastIndex = match.index + match[0].length;
    }
    result += esc(text.slice(lastIndex));
    return result;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function field(label, content) {
    if (!content) return '';
    return `<div class="rp-section"><div class="rp-section-label">${esc(label)}</div><div class="rp-section-content">${esc(content)}</div></div>`;
}

function fmtTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function esc(str) {
    if (!str) return '';
    str = String(str);
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showError(msg) {
    document.getElementById('error-text').textContent = msg;
    document.getElementById('error-section').classList.remove('hidden');
    document.getElementById('analyze-btn').disabled = false;
}

document.getElementById('url-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') startAnalysis();
});
