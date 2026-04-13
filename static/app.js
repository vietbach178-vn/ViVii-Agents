let currentJobId = null;
let activePolls = {}; // jobId -> intervalId — track multiple running jobs
let currentTranscript = null;
let richPointWords = [];
let currentJokes = [];
let activeHistoryId = null;

// Load history on page load
document.addEventListener('DOMContentLoaded', () => {
    fetchHistory();
});

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

        // Extract video ID for display
        const videoId = extractVideoId(item.url);
        const displayUrl = videoId || item.url;

        // Format time
        let timeStr = '';
        if (item.created_at) {
            const d = new Date(item.created_at);
            timeStr = d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
        }

        el.innerHTML = `
            <div class="sidebar-url" title="${esc(item.url)}">${esc(displayUrl)}</div>
            <div class="sidebar-stats">
                <span>${item.rich_points_count} rich points</span>
                <span>${item.jokes_count} jokes</span>
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
                fetchHistory(); // refresh active state
            }
        });
}

function startAnalysis() {
    const url = document.getElementById('url-input').value.trim();
    if (!url) return;

    // Clear input for next paste
    document.getElementById('url-input').value = '';

    // Show status for this job
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
        if (data.error) {
            showError(data.error);
            return;
        }
        currentJobId = data.job_id;
        // Add to sidebar as "processing"
        addProcessingToSidebar(data.job_id, url);
        // Start polling this job
        activePolls[data.job_id] = setInterval(() => pollJob(data.job_id), 1500);
    })
    .catch(err => showError(err.message));
}

function addProcessingToSidebar(jobId, url) {
    const list = document.getElementById('sidebar-list');
    // Remove "no videos" message
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
        // Switch to view this job's progress
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
            // Update status bar only if this is the currently viewed job
            if (jobId === currentJobId) {
                document.getElementById('status-text').textContent = job.message;
                updateSteps(job.status);
            }

            if (job.status === 'done') {
                clearInterval(activePolls[jobId]);
                delete activePolls[jobId];

                // If this is the currently viewed job, show results
                if (jobId === currentJobId) {
                    document.getElementById('status-section').classList.add('hidden');
                    activeHistoryId = jobId;
                    renderResults(job);
                }

                // Update sidebar
                fetchHistory();

            } else if (job.status === 'error') {
                clearInterval(activePolls[jobId]);
                delete activePolls[jobId];

                if (jobId === currentJobId) {
                    document.getElementById('status-section').classList.add('hidden');
                    showError(job.message);
                }

                // Remove processing item from sidebar
                const el = document.getElementById(`sidebar-${jobId}`);
                if (el) el.remove();
            }
        });
}

function resetSteps() {
    ['step-fetch', 'step-scan', 'step-l1', 'step-l2', 'step-jokes'].forEach(id => {
        document.getElementById(id).classList.remove('active', 'done');
    });
}

function updateSteps(status) {
    const order = ['fetching', 'scanning', 'level1', 'level2', 'jokes', 'done'];
    const stepMap = { fetching: 'step-fetch', scanning: 'step-scan', level1: 'step-l1', level2: 'step-l2', jokes: 'step-jokes' };
    const currentIdx = order.indexOf(status);

    Object.entries(stepMap).forEach(([key, id]) => {
        const el = document.getElementById(id);
        const idx = order.indexOf(key);
        el.classList.remove('active', 'done');
        if (idx < currentIdx) el.classList.add('done');
        else if (idx === currentIdx) el.classList.add('active');
    });

    if (status === 'done') {
        Object.values(stepMap).forEach(id => {
            const el = document.getElementById(id);
            el.classList.remove('active');
            el.classList.add('done');
        });
    }
}

function renderResults(job) {
    const section = document.getElementById('results-section');
    const meta = document.getElementById('results-meta');
    const list = document.getElementById('results-list');
    const results = job.results || [];

    // Collect rich point words for transcript highlighting
    richPointWords = results.map(rp => rp.word.toLowerCase());

    meta.textContent = `${results.length} rich point(s) found`;

    list.innerHTML = '';

    if (results.length === 0) {
        list.innerHTML = '<p style="color:#888;text-align:center;padding:40px 0;">No rich points found in this video.</p>';
    } else {
        results.forEach((rp, i) => {
            const card = document.createElement('div');
            card.className = 'rp-card' + (i === 0 ? ' open' : '');
            card.innerHTML = buildCard(rp);
            card.querySelector('.rp-card-header').addEventListener('click', () => {
                card.classList.toggle('open');
            });
            list.appendChild(card);
        });
    }

    // Store jokes for transcript highlighting
    currentJokes = job.jokes || [];

    // Render jokes
    renderJokes(currentJokes);

    // Render transcript (with joke highlights)
    renderTranscript(job.transcript || [], job.word_count || 0);

    // Show video URL
    const urlBar = document.getElementById('video-url-bar');
    const videoUrl = job.url || '';
    if (videoUrl) {
        urlBar.innerHTML = `<a href="${esc(videoUrl)}" target="_blank">${esc(videoUrl)}</a>`;
    } else {
        urlBar.innerHTML = '';
    }

    document.getElementById('welcome-section').classList.add('hidden');
    section.classList.remove('hidden');
}

function renderTranscript(segments, wordCount) {
    const body = document.getElementById('transcript-body');
    const meta = document.getElementById('transcript-meta');

    meta.textContent = `${wordCount.toLocaleString()} words`;

    if (!segments || segments.length === 0) {
        body.innerHTML = '<p style="color:#555;">No transcript available.</p>';
        return;
    }

    // Build a map: for each transcript line, find which joke(s) it belongs to
    const jokeLineMap = buildJokeLineMap(segments, currentJokes);

    let html = '';
    segments.forEach((seg, idx) => {
        const mins = Math.floor(seg.start / 60);
        const secs = Math.floor(seg.start % 60);
        const ts = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        const highlighted = highlightRichPoints(seg.text);

        const jokeIdx = jokeLineMap[idx];
        if (jokeIdx !== undefined) {
            html += `<div class="transcript-line joke-line" data-joke="${jokeIdx}" onclick="scrollToJoke(${jokeIdx})"><span class="transcript-ts">${ts}</span>${highlighted}</div>`;
        } else {
            html += `<div class="transcript-line"><span class="transcript-ts">${ts}</span>${highlighted}</div>`;
        }
    });

    body.innerHTML = html;
}

function highlightRichPoints(text) {
    if (richPointWords.length === 0) return esc(text);

    // Sort by length descending so longer phrases match first
    const sorted = [...richPointWords].sort((a, b) => b.length - a.length);

    // Build regex that matches any rich point word/phrase (case-insensitive)
    const escaped = sorted.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const pattern = new RegExp('\\b(' + escaped.join('|') + ')\\b', 'gi');

    // Split text into parts, escaping non-match parts and wrapping matches
    let result = '';
    let lastIndex = 0;
    let match;

    // Reset regex
    pattern.lastIndex = 0;

    while ((match = pattern.exec(text)) !== null) {
        // Add text before match (escaped)
        result += esc(text.slice(lastIndex, match.index));
        // Add highlighted match
        result += `<span class="highlight">${esc(match[0])}</span>`;
        lastIndex = match.index + match[0].length;
    }
    // Add remaining text
    result += esc(text.slice(lastIndex));

    return result;
}

function buildJokeLineMap(segments, jokes) {
    // For each transcript line, check if it's part of a joke excerpt
    // Returns: { lineIndex: jokeIndex }
    const map = {};
    if (!jokes || jokes.length === 0) return map;

    // Normalize text for fuzzy matching
    const norm = (s) => s.toLowerCase().replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim();

    jokes.forEach((joke, jokeIdx) => {
        if (!joke.transcript_excerpt) return;
        const excerptNorm = norm(joke.transcript_excerpt);

        // Try to find which transcript lines are part of this joke
        // Strategy: check if each line's text appears as a substring of the excerpt
        segments.forEach((seg, lineIdx) => {
            if (map[lineIdx] !== undefined) return; // already claimed
            const lineNorm = norm(seg.text);
            if (lineNorm.length < 3) return; // skip tiny lines
            if (excerptNorm.includes(lineNorm)) {
                map[lineIdx] = jokeIdx;
            }
        });
    });

    return map;
}

function scrollToJoke(jokeIdx) {
    const cards = document.querySelectorAll('.joke-card');
    if (jokeIdx >= 0 && jokeIdx < cards.length) {
        const card = cards[jokeIdx];
        card.classList.add('open');
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Flash effect
        card.style.borderColor = '#f59e0b';
        setTimeout(() => { card.style.borderColor = ''; }, 2000);
    }
}

function renderJokes(jokes) {
    const section = document.getElementById('jokes-section');
    const meta = document.getElementById('jokes-meta');
    const list = document.getElementById('jokes-list');

    if (!jokes || jokes.length === 0) {
        section.classList.add('hidden');
        return;
    }

    meta.textContent = `${jokes.length} joke(s) explained`;
    list.innerHTML = '';

    jokes.forEach((joke, i) => {
        const card = document.createElement('div');
        card.className = 'joke-card' + (i === 0 ? ' open' : '');
        card.innerHTML = buildJokeCard(joke);
        card.querySelector('.joke-card-header').addEventListener('click', () => {
            card.classList.toggle('open');
        });
        list.appendChild(card);
    });

    section.classList.remove('hidden');
}

function buildJokeCard(joke) {
    const ts = joke.timestamp || 0;
    const mins = Math.floor(ts / 60);
    const secs = Math.floor(ts % 60);
    const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    const preview = (joke.explanation || '').slice(0, 60) + ((joke.explanation || '').length > 60 ? '...' : '');

    return `
        <div class="joke-card-header">
            <div style="display:flex;align-items:center;flex:1;min-width:0;">
                <span class="joke-type">${esc(joke.joke_type || 'joke')}</span>
                <span class="joke-ts">${timeStr}</span>
                <span class="joke-preview">${esc(preview)}</span>
            </div>
            <span class="rp-toggle">&#x25BC;</span>
        </div>
        <div class="joke-card-body">
            ${joke.transcript_excerpt ? `<div class="joke-excerpt">${esc(joke.transcript_excerpt)}</div>` : ''}
            ${joke.explanation ? `<div class="joke-explanation">${esc(joke.explanation)}</div>` : ''}
            ${joke.cultural_context ? `
                <div class="joke-cultural">
                    <div class="joke-cultural-label">Cultural context</div>
                    ${esc(joke.cultural_context)}
                </div>
            ` : ''}
        </div>
    `;
}

function buildCard(rp) {
    const ts = rp.timestamp_seconds || 0;
    const mins = Math.floor(ts / 60);
    const secs = Math.floor(ts % 60);
    const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    const related = (rp.related_rich_points || []).map(r => `<span class="rp-tag">${esc(r)}</span>`).join('');

    return `
        <div class="rp-card-header">
            <div>
                <span class="rp-word">${esc(rp.word)}</span>
                <span class="rp-meta">${esc(rp.type || '')} · ${esc(rp.pos || '')} · ${esc(rp.sense_tag || '')}</span>
            </div>
            <span class="rp-toggle">&#x25BC;</span>
        </div>
        <div class="rp-card-body">
            ${field('Definition', rp.definition)}
            ${field('Meaning in this video', rp.context_meaning)}
            ${rp.transcript_quote ? `
                <div class="rp-section">
                    <div class="rp-section-label">From the transcript <span class="rp-timestamp">${timeStr}</span></div>
                    <div class="rp-section-content rp-quote">${esc(rp.transcript_quote)}</div>
                </div>
            ` : ''}
            <div class="rp-divider"></div>
            ${field('Why is this a rich point?', rp.why_rich_point)}
            ${field('What if you use it wrong?', rp.misuse_consequence)}
            ${field('Origin', rp.origin_story)}
            ${field('When to use / not use', rp.when_to_use)}
            ${related ? `
                <div class="rp-section">
                    <div class="rp-section-label">Related rich points</div>
                    <div class="rp-tags">${related}</div>
                </div>
            ` : ''}
            ${field('How to say it as an outsider', rp.outsider_rephrase)}
        </div>
    `;
}

function field(label, content) {
    if (!content) return '';
    return `
        <div class="rp-section">
            <div class="rp-section-label">${esc(label)}</div>
            <div class="rp-section-content">${esc(content)}</div>
        </div>
    `;
}

function esc(str) {
    if (!str) return '';
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
