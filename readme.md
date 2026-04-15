# Agent: Rich Point Discovery

Multi-agent system phát hiện **cultural rich points** (Michael Agar) từ transcript YouTube video bằng AI. Thay vì match against danh sách có sẵn, AI tự đọc transcript và phát hiện từ/cụm từ mang tải văn hoá Mỹ mà non-American sẽ không hiểu.

---

## Architecture

```mermaid
flowchart TD
    A["YouTube URL"] --> B

    subgraph Transcript Processing
        B["Transcript Fetcher\n<i>Python · youtube-transcript-api</i>"]
        B -->|raw segments| C["Sentence Merger\n<i>Python heuristic</i>\ntime gap · punctuation · markers"]
        C -->|câu thô| D["A1 Sentence Splitter\n<i>LLM · per sentence</i>\ndetect speaker changes\n+ anti-hallucination verify"]
        D -->|câu hoàn chỉnh| E["Chunker\n<i>Python</i>\n~4K words/chunk"]
    end

    subgraph "B-series · Rich Point Discovery"
        E -->|chunks| F["B1 Scanner Agent\n<i>LLM · per chunk</i>\nAgar test 5 criteria\n+ regex verify"]
        F -->|verified candidates| G["B2 Level 1 Agent\n<i>LLM · per video</i>\nDefinition · Context · Quote"]
        G -->|rich points + sentences| H["B3 Level 2 Agent\n<i>LLM · per video</i>\n6 fields phân tích sâu"]
    end

    H --> J["Rich Point Output\n<i>9 fields per rich point</i>"]

    subgraph "C-series · Joke Pipeline (standalone)"
        T["transcript.json"] --> C1["C1 Joke Detector\n<i>LLM · 1 call cho full transcript</i>\ntopic blocks + nested punchlines"]
        C1 -->|c1_output.json| C2["C2 Joke Explainer\n<i>LLM · per topic block</i>\n2-tier: tier_1_topic + tier_2_bits"]
        C2 --> C3["C3 Comprehension MCQ\n<i>LLM · 1 MCQ per bit</i>\n3 options (1 correct + 2 wrong)"]
        C3 --> C4A["c3_output.json"]
    end

    subgraph "D-series · Cultural Stamps"
        C2 --> D1["D1 Stamp Detector\n<i>LLM + code canonicalize</i>\nopen-name → fuzzy match catalog"]
        D1 --> D2["D2 Stamp Deep-Dive\n<i>LLM · long-form article</i>\nTL;DR + 4 sections, cached"]
        D1 --> C4["C4 Transfer Practice MCQ\n<i>LLM · stamp or topic mode</i>\n3-option new-context MCQ"]
        D2 --> D2A["d2_articles/*.json"]
        C4 --> C4B["c4_output.json"]
    end

    style B fill:#1a1a2e,stroke:#4ade80,color:#fff
    style C fill:#1a1a2e,stroke:#666,color:#fff
    style D fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style E fill:#1a1a2e,stroke:#666,color:#fff
    style F fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style G fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style H fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style J fill:#1a1a2e,stroke:#4ade80,color:#fff
    style T fill:#1a1a2e,stroke:#4ade80,color:#fff
    style C1 fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style C2 fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style C3 fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style C4 fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style C4A fill:#1a1a2e,stroke:#4ade80,color:#fff
    style C4B fill:#1a1a2e,stroke:#4ade80,color:#fff
    style D1 fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style D2 fill:#1a1a2e,stroke:#f59e0b,color:#fff
    style D2A fill:#1a1a2e,stroke:#4ade80,color:#fff
```

> Nodes viền vàng = LLM agent. Nodes viền xanh = Python / input-output. Nodes viền xám = Python heuristic.

---

## Agents chi tiết

### Transcript Fetcher (`transcript.py`)

Không phải AI agent. Dùng `youtube-transcript-api` để lấy auto-caption từ YouTube.

- **Input:** YouTube URL
- **Output:** `{ segments, sentences, full_text, word_count }`
- **Lưu ý:** Một số video không có caption → skip với error

### Sentence Merger + Splitter + Chunker (`chunker.py`)

Ba bước xử lý:

**Bước 1 — Segments → Sentences thô** (`segments_to_sentences`, heuristic)

YouTube auto-caption trả về mảnh nhỏ (2-5 từ/segment). Function này merge thành câu dựa trên:
- **Time gap** giữa segments (>1s = câu mới)
- **Dấu câu** cuối segment (`. ? !` = câu mới)
- **Bracketed markers** (`[Laughter]`, `[Music]` → standalone)
- **Max 80 words/câu** (force split nếu quá dài)

Ví dụ: 290 segments → 45 câu thô.

**Bước 2 — LLM Sentence Splitter** (`split_sentences_with_llm`, AI agent)

Gửi tất cả câu thô cho LLM để split thành câu nhỏ hơn. LLM detect:
- **Đổi người nói** (question → answer, interjection)
- **Ngữ pháp lệch** (chuyển chủ ngữ, đổi context)
- **Short utterances** ("yeah", "no", "oh" → tách riêng)

- **Model:** `meta-llama/llama-4-scout-17b-16e-instruct` (Groq)
- **Anti-hallucination verify:** Sau khi LLM trả kết quả, code join tất cả parts lại và so sánh với text gốc. Nếu khác bất kỳ từ nào → reject, giữ câu gốc.
- **Rule cho LLM:** CHỈ được chèn ranh giới ngắt, KHÔNG được thêm/xóa/sửa bất kỳ từ nào.

Ví dụ: 45 câu thô → 367 câu hoàn chỉnh.

**Bước 3 — Sentences → Chunks** (`sentences_to_chunks`)

Nhóm các câu thành chunks ~4K words cho Scanner. Không bao giờ cắt giữa câu.

### B1 — Scanner Agent ([agents/B1_scanner/](agents/B1_scanner/))

AI agent đầu tiên. Đọc từng chunk transcript và phát hiện candidate rich points.

- **Model:** `meta-llama/llama-4-scout-17b-16e-instruct` (Groq)
- **Input:** 1 chunk transcript (~4K words)
- **Output:** JSON list candidates `{ word, type, pos, sense_tag, agar_score }`
- **Prompt core:**
  - Định nghĩa rich point theo Michael Agar
  - 5 tiêu chí Agar test (cần ≥3/5)
  - Negative examples (tránh over-flag: "cool", "gonna", "rice"...)
  - **Critical rule:** CHỈ trả về từ thực sự có trong transcript text
- **Anti-hallucination:** Sau khi LLM trả kết quả, code check bằng regex xem từ có tồn tại trong transcript không. Không có → drop ngay + log. Đây là fix cho vấn đề LLM hallucinate từ không có trong text (vd: trả "cookout" dù transcript không có từ này).

### B2 — Level 1 Agent ([agents/B2_level1/](agents/B2_level1/))

Nhận candidates đã verified → generate 3 fields "hiểu từ".

- **Model:** `meta-llama/llama-4-scout-17b-16e-instruct` (Groq)
- **Input:** Candidate list + relevant sentences (chỉ câu chứa candidate + 1 câu context trước/sau — tiết kiệm tokens)
- **Output:** JSON `{ word, type, pos, sense_tag, definition, context_meaning, transcript_quote, timestamp_seconds }`
- **3 fields:**

| # | Field | Mô tả |
|---|-------|-------|
| 1 | Definition | Urban Dictionary style, English đơn giản, giải thích cultural sense |
| 2 | Context meaning | Nghĩa cụ thể trong video này, tham chiếu tình huống |
| 3 | Transcript quote + timestamp | Trích exact câu từ transcript, kèm timestamp |

### B3 — Level 2 Agent ([agents/B3_level2/](agents/B3_level2/))

Nhận Level 1 output → thêm 6 fields phân tích văn hoá sâu.

- **Model:** `meta-llama/llama-4-scout-17b-16e-instruct` (Groq)
- **Input:** Level 1 rich points (đã có definition + context)
- **Output:** JSON `{ word, sense_tag, why_rich_point, misuse_consequence, origin_story, when_to_use, related_rich_points, outsider_rephrase }`
- **6 fields:**

| # | Field | Mô tả |
|---|-------|-------|
| 4 | Why rich point | Giải thích rupture: non-American sẽ hiểu sai/miss gì |
| 5 | Misuse consequence | Người Mỹ react thế nào nếu outsider dùng sai |
| 6 | Origin story | Từ đâu ra, community nào, thập kỷ nào |
| 7 | When to use | Register, audience, setting |
| 8 | Related rich points | 2-4 từ liên quan (cùng subculture, cùng function) |
| 9 | Outsider rephrase | Nói cách khác nếu chưa sẵn sàng dùng từ gốc |

### ~~Joke Agent~~ (archived — `.archive/agents/A5_joke/`)

**Deprecated.** Old in-line joke analyzer that ran song song với Level 2. Replaced by the standalone C-series joke pipeline (C1 + C2) — see bottom of readme. Kept in `.archive/` for reference only.

<details>
<summary>Historical description</summary>

Chạy song song với Level 2. Phân tích toàn bộ transcript và giải thích mọi joke/bit/reference. Cũng gắn **dark humor mechanism tags** để Exercise Builder dùng downstream.

- **Model:** Primary model từ `config.py`
- **Input:** Full transcript (sentences) + Level 1 rich points (cho context)
- **Output:** JSON `{ transcript_excerpt, timestamp, joke_type, explanation, cultural_context, mechanisms, taboo_intensity }`
- **7 fields per joke:**

| # | Field | Mô tả |
|---|-------|-------|
| 1 | Transcript excerpt | Đoạn transcript chứa joke (verbatim, có thể nhiều câu) |
| 2 | Timestamp | Timestamp bắt đầu joke |
| 3 | Joke type | observational, crowd-work, self-deprecating, cultural-reference, wordplay, roast, callback... |
| 4 | Explanation | Giải thích joke — tại sao funny với American audience, đang mock/subvert cái gì |
| 5 | Cultural context | Kiến thức văn hoá non-American cần biết để hiểu joke (nếu có) |
| 6 | Mechanisms | Mảng tag từ 5 core dark humor mechanisms. Rỗng nếu joke không phải dark humor. |
| 7 | Taboo intensity | `mild` / `medium` / `extreme` / rỗng. `extreme` = cross red line, Exercise Builder sẽ skip |

- **Batching:** Transcript dài được chia thành batch ~3K words, mỗi batch 1 LLM call
- **Dùng cho:** Video standup comedy — phần lớn nội dung đang nói kháy hoặc refer tới cultural context
- **Mechanism rubric:** `.archive/agents/A5_joke/mechanism_rubric.py` — 5 core dark humor mechanisms (source of truth cho workflow cũ).

</details>

### ~~Exercise Builder Workflow~~ (archived — `.archive/agents/A6_exercise_builder/`)

**Deprecated.** Old graduated-MCQ workflow driven by A5 joke tags. Replaced by upcoming D-series work (cultural stamps + practice). Kept in `.archive/` for reference.

<details>
<summary>Historical description</summary>

**Không phải agent — đây là một Workflow** (Prompt Chain + Evaluator-Optimizer). Control flow do code điều khiển, LLM chỉ thực thi từng node. Lý do chọn Workflow thay vì Agent: các bước cố định, dễ eval, dễ debug, chi phí dự đoán được. Xem `groovy-wiggling-tower.md` trong thư mục plans để hiểu quyết định thiết kế.

- **Input:** `JokeOutput` từ Joke Agent
- **Output:** `ExerciseSet` — list of graduated multiple-choice exercises
- **Điều kiện kích hoạt:** chỉ sinh exercise cho jokes có `mechanisms` không rỗng và `taboo_intensity` không phải `extreme`. Video không có dark humor → output rỗng, không tốn token.

**5 nodes:**

1. **Parse & Route** (code) — lọc jokes, tạo list `(joke, mechanism)` pairs, 1 pair sinh 1 MCQ
2. **Generate MCQ** (LLM, `GENERATE_SYSTEM`) — sinh graduated MCQ: A miss / B almost / C land
3. **Evaluator Check** (LLM, `EVALUATE_SYSTEM`) — chấm 4 tiêu chí: incongruity, coherence, graduation, taste. Fail → retry tối đa 2 lần
4. **Explanation** (LLM, `EXPLAIN_SYSTEM`) — viết why C lands, why B misses, pattern takeaway
5. **Aggregate** (code) — shuffle vị trí đáp án đúng (không phải lúc nào C cũng đúng), assemble Exercise object

**Graduated structure (quy tắc cốt lõi):**
- **A** = phản ứng bình thường, không có attempt humor
- **B** = có attempt mechanism nhưng weak (almost)
- **C** = mechanism landed fully

Sau khi shuffle vị trí, `correct` field trong output cho biết letter nào là đáp án đúng.

**Mechanism taxonomy (5 core, import từ Joke Agent):**

| ID | Mô tả ngắn |
|----|------------|
| `misdirection` | Setup dẫn expectation một hướng, punchline flip |
| `taboo_violation` | Chạm chủ đề cấm (death, disaster, race, religion, sex) |
| `benign_violation` | Vi phạm norm nhưng vẫn "safe" (McGraw-Warren 2010) |
| `absurd_juxtaposition` | Nghiêm túc + ngớ ngẩn crash cùng context |
| `subverted_solemnity` | Giọng thờ ơ với chủ đề nghiêm trọng |

**Red lines:** mock nạn nhân thật còn sống, punch down vào protected groups bằng superiority thuần, platform hate framing → Joke Agent set `taboo_intensity="extreme"`, Exercise Builder skip.

- **Retry policy:** mỗi (joke, mechanism) pair tối đa 2 retry nếu evaluator fail. Sau đó drop.
- **Rate limit:** sleep 2s giữa các LLM call (Groq free tier friendly)

</details>

---

## Rich Point là gì?

Theo nhà ngôn ngữ học Michael Agar:

> "A rich point is a moment when cultural/linguistic difference breaks your expectations, creating misunderstanding — and that very misunderstanding becomes the starting point for discovering and learning a new system of meaning."

**5 tiêu chí Agar test** (cần đạt ≥3/5):

1. **Translation collapse** — dịch literal mất tầng văn hoá
2. **Expectation breaking** — outsider nói "what does that mean?"
3. **Cultural background required** — cần biết bối cảnh Mỹ
4. **No 1:1 equivalent** — hầu hết văn hoá không có tương đương
5. **Insider signal** — dùng đúng = thuộc nhóm, dùng sai = outsider

Chi tiết: xem [`word-logic.md`](../Tool-Video-Richpoint%20Mapping/word-logic.md)

---

## File structure

Mỗi sub-agent sống trong thư mục riêng dưới `agents/`. Prompt system của từng agent nằm cạnh code của chính nó, **không** dồn vào một file chung.

```
Agent-Richpoint-Discovery/
  main.py              CLI entry point
  app.py               Web UI (Flask)
  config.py            API key, model names, chunk settings
  transcript.py        YouTube transcript fetching + sentence building
  chunker.py           Pure-Python heuristic: segments → sentences → chunks
  llm_utils.py         Shared LLM call helper (error handling, JSON extraction)
  aggregator.py        Merge levels + markdown output
  schemas.py           Pydantic models (tolerant — coerce null → defaults)
  requirements.txt     Dependencies
  CLAUDE.md            Project rules

  agents/              ← Mỗi sub-agent = 1 thư mục, prompt lưu riêng
    __init__.py        Re-exports all agent entry points
    A1_splitter/                 ← A-series: shared preprocessing
      agent.py         LLM-based sentence splitter (anti-hallucination verify)
      prompt.py        SPLITTER_SYSTEM
    B1_scanner/                  ← B-series: Rich Point Discovery
      agent.py         Scanner agent + regex verification
      prompt.py        SCANNER_SYSTEM
    B2_level1/
      agent.py         Level 1 agent (definition / context / quote)
      prompt.py        LEVEL1_SYSTEM
    B3_level2/
      agent.py         Level 2 agent (6 deep-analysis fields)
      prompt.py        LEVEL2_SYSTEM
    C1_joke_detector/            ← C-series: Joke pipeline (standalone)
      agent.py              Topic blocks + punchlines
      prompt.py             JOKE_DETECTOR_SYSTEM
    C2_joke_explainer/
      agent.py              Per-block 2-tier output (tier_1_topic + tier_2_bits)
      prompt.py             JOKE_EXPLAINER_SYSTEM
    C3_comprehension_mcq/
      agent.py              1 MCQ per bit (3 options) + position shuffle
      prompt.py             C3_SYSTEM
    C4_transfer_practice/
      agent.py              Stamp-mode or topic-mode transfer MCQ
      prompt.py             C4_STAMP_SYSTEM + C4_TOPIC_SYSTEM
    D1_stamp_detector/            ← D-series: Cultural Stamps
      agent.py              LLM open-name + code canonicalize (rapidfuzz)
      prompt.py             D1_SYSTEM
      catalog.json          Persisted canonical stamps + aliases (grows organically)
    D2_stamp_deep_dive/
      agent.py              Long-form article per canonical stamp, file-cached
      prompt.py             D2_SYSTEM

  .archive/agents/     ← Deprecated agents, kept for reference
    A5_joke/           (old joke analyzer with dark-humor mechanism tags)
    A6_exercise_builder/  (old graduated-MCQ workflow — replaced by C-series)

  templates/
    index.html         Web UI template
  static/
    style.css          Dark theme, two-column layout
    app.js             Frontend logic + transcript highlighting
```

**Import pattern:** entry points (`main.py`, `app.py`) import từ `agents` package:

```python
from agents import (
    split_sentences_with_llm,   # A1
    scan_all_chunks,            # B1
    run_level1,                 # B2
    run_level2,                 # B3
    run_joke_detector,          # C1
    run_joke_explainer,         # C2
    run_c3,                     # C3 — comprehension MCQ
    run_c4,                     # C4 — transfer practice MCQ
    run_d1,                     # D1 — stamp detector + canonicalize
    run_d2,                     # D2 — stamp deep-dive article
)
```

---

## Cách chạy

### CLI

```bash
cd Agent-Richpoint-Discovery
pip install -r requirements.txt

GROQ_API_KEY="your-key" python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Output: `result.md`

### Web UI

```bash
GROQ_API_KEY="your-key" python app.py
```

Mở http://localhost:5001 → paste YouTube URL → nhấn Analyze.

Giao diện two-column:
- **Trái:** Rich point cards (mở/đóng, 9 fields) + Joke cards (viền vàng, mở/đóng)
- **Phải:** Full transcript hiển thị theo câu hoàn chỉnh, mỗi câu có timestamp, rich points được highlight vàng

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `groq` | LLM API client |
| `youtube-transcript-api` | Fetch YouTube captions (no API key) |
| `pydantic` | Structured output validation |
| `flask` | Web UI server |
| `rapidfuzz` | D1 stamp canonicalization (fuzzy alias matching) |

---

## Rate limiting (Groq free tier)

- **100K tokens/ngày/model** — khi hết quota 1 model, đổi sang model khác trong `config.py`
- **12K tokens/phút** — tool tự batch 3 candidates/lần và delay 10s giữa các batch
- Với Groq paid tier hoặc Claude API, có thể bỏ delay và chạy parallel

---

## Thay đổi LLM provider

Sửa `config.py` để đổi model. Sửa `agents/<name>/agent.py` để đổi API client (Groq → Anthropic/OpenAI). Prompt system của mỗi agent nằm tại `agents/<name>/prompt.py` và không phụ thuộc provider.

## Sửa prompt của một agent

Mỗi agent có file prompt riêng — muốn chỉnh prompt của Scanner chỉ cần mở `agents/B1_scanner/prompt.py`, không ảnh hưởng các agent khác.

---

## C/D Joke & Stamp Pipeline — standalone

Pipeline **độc lập** với flow rich-point. Dùng để phân tích stand-up comedy + sinh practice content về joke và culture stamps cho người học. Grounded vào taxonomy ở [`../05. Content-builder-agent/05.joke-structure.md`](../05.%20Content-builder-agent/05.joke-structure.md).

```
transcript.json
      │
      ▼
C1 joke_detector ──▶ c1_output.json (topic blocks + punchlines)
      │
      ▼
C2 joke_explainer ──▶ c2_output.json (2-tier: tier_1_topic + tier_2_bits)
      ├──────────────▶ C3 comprehension_mcq  ──▶ c3_output.json (1 MCQ per bit)
      │
      └──────────────▶ D1 stamp_detector      ──▶ d1_output.json (canonicalized stamps)
                              ├──────────────▶ D2 stamp_deep_dive ──▶ d2_output.json + d2_articles/*.json
                              └──────────────▶ C4 transfer_practice ──▶ c4_output.json
```

### C1 — Joke Detector ([agents/C1_joke_detector/](agents/C1_joke_detector/))

- Input: 1 transcript JSON (sentences với timestamp).
- Output: list `topic_blocks`, mỗi block chứa `title`, `premise`, sentence range, time range, và mảng `punchlines` lồng bên trong.
- Model: `JOKE_DETECTOR_MODEL` trong `config.py` (structural segmentation — mid-size model đủ).
- 1 LLM call cho toàn bộ transcript.

### C2 — Joke Explainer ([agents/C2_joke_explainer/](agents/C2_joke_explainer/))

- Input: full transcript + 1 topic block từ C1.
- Output per block (**2-tier schema**):
  - `tier_1_topic`: `topic_label` + `topic_summary` + `cultural_domain` — high-level "what the bit is ABOUT", không đụng joke analysis.
  - `tier_2_bits[]`: mỗi element là một comedic beat với `bit_id`, `sentence_idx`, `text_excerpt`, `why_funny`, `primary_mechanism`, `mechanisms_all[]`.
  - `theory_scores` (block-level) + `text_dependency_notes`.
- Model: `JOKE_EXPLAINER_MODEL` (reasoning mạnh).
- 1 LLM call mỗi topic block.
- **Tier separation rules:** `tier_1_topic` NOT mention jokes/mechanisms. `tier_2_bits` NOT repeat topic_summary.

### C3 — Comprehension MCQ ([agents/C3_comprehension_mcq/](agents/C3_comprehension_mcq/))

- Input: C2.tier_2_bits (per block).
- Output: 1 MCQ per bit, mỗi MCQ có `question` + `options` (3 keys A/B/C) + `correct` + `explanation` (why_correct + 2 why_wrong).
- Rule: correct answer phải reference `primary_mechanism` của bit. Code shuffle vị trí correct letter sau khi LLM trả về để tránh bias.
- Model: `JOKE_EXPLAINER_MODEL`.

### D1 — Culture Stamp Detector ([agents/D1_stamp_detector/](agents/D1_stamp_detector/))

- Input: C2 output (both tiers) per topic block.
- Two-step:
  1. **LLM propose** — đọc C2.tier_1_topic + tier_2_bits, sinh stamps với tên tự do (open taxonomy).
  2. **Code canonicalize** — normalize name → exact match alias → rapidfuzz fuzzy match (≥85 score) → auto-add new entry. Catalog persist tại [`agents/D1_stamp_detector/catalog.json`](agents/D1_stamp_detector/catalog.json).
- Output: stamps per block với `canonical_name`, `llm_proposed_name`, `category`, `confidence`, `evidence`, `source_tier`.
- Model: `JOKE_DETECTOR_MODEL` (detection đủ cheap model).
- **Empty OK:** joke không có stamp → `stamps: []`. D2 skip block đó, C4 fallback sang topic mode.

### D2 — Stamp Deep-Dive ([agents/D2_stamp_deep_dive/](agents/D2_stamp_deep_dive/))

- Input: 1 canonical stamp name + category từ D1.
- Output: long-form article 1000-2000 words với schema `{ stamp_canonical_name, tl_dr, sections: {historical_context, cultural_significance, common_misunderstandings, related_references}, word_count }`.
- **TL;DR mandatory** ≤100 words ở đầu article (scannable cho student).
- **Caching:** file-based cache tại `<output_dir>/d2_articles/<slug>.json`. Cùng canonical stamp → cache hit, không gọi LLM lại. Grown across pipeline runs.
- Model: `JOKE_EXPLAINER_MODEL`.

### C4 — Transfer Practice MCQ ([agents/C4_transfer_practice/](agents/C4_transfer_practice/))

- Input: D1 stamps + C2 tier_1_topic per block.
- Two modes:
  - **Stamp mode** (khi block có ≥1 stamp): mỗi stamp → 1 MCQ test "nhận biết stamp này ở context mới" (fresh fictional quote, không dùng lại joke gốc). Distractors reference stamps KHÁC.
  - **Topic fallback mode** (khi D1 rỗng): fallback sang `tier_1_topic.topic_label`, sinh 1 MCQ test "nhận biết joke cùng topic ở context khác".
- Output: 3-option MCQs với position shuffle.
- Model: `JOKE_EXPLAINER_MODEL`.

### Chạy pipeline

```bash
python joke_pipeline.py Sample/Transcript-sample.json Sample/
# → Sample/c1_output.json
# → Sample/c2_output.json   (2-tier)
# → Sample/c3_output.json
# → Sample/d1_output.json
# → Sample/d2_output.json + Sample/d2_articles/*.json
# → Sample/c4_output.json
```

Pipeline order: C1 → C2 → C3 → D1 → D2 → C4. C3 chỉ cần C2; D2 và C4 chỉ cần D1 (và C2 cho C4 grounding).

### Test không dùng Python (paste prompt vào Claude Code)

Mỗi agent có 1 file `prompt.md` self-contained:

- [agents/C1_joke_detector/prompt.md](agents/C1_joke_detector/prompt.md)
- [agents/C2_joke_explainer/prompt.md](agents/C2_joke_explainer/prompt.md)
- [agents/C3_comprehension_mcq/prompt.md](agents/C3_comprehension_mcq/prompt.md)
- [agents/C4_transfer_practice/prompt.md](agents/C4_transfer_practice/prompt.md)
- [agents/D1_stamp_detector/prompt.md](agents/D1_stamp_detector/prompt.md)
- [agents/D2_stamp_deep_dive/prompt.md](agents/D2_stamp_deep_dive/prompt.md)

### Liên kết với báo cáo lý thuyết

C2 explicitly tham chiếu `05.joke-structure.md`:
- 4 lý thuyết trong `theory_scores` = §2 của report.
- 10 mechanism labels = §4 của report.
- `text_dependency_notes` bám theo §3.5 / §4 bảng text-analyzability.

