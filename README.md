# Semantic Surfer

## Transcription & Analysis Tool for GitEnglishHub

*Last Updated: December 8, 2025*

---

## ⚠️ THIS IS NOT GITENGLISHHUB

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Semantic Surfer is a TOOL that sends data to GitEnglishHub.  │
│                                                                 │
│   It's like a microphone or a scanner.                         │
│   You buy a scanner. You use the scanner.                      │
│   The scanner is not your filing cabinet.                      │
│                                                                 │
│   Semantic Surfer = The scanner (captures & analyzes data)     │
│   GitEnglishHub = The filing cabinet (stores data)             │
│                                                                 │
│   DO NOT MERGE THEM. DO NOT COPY CODE BETWEEN THEM.            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## What This Tool Does

1. **Records audio** (microphone or file)
2. **Sends to AssemblyAI** for transcription with speaker diarization
3. **Runs local analysis** (speaking rate, pauses, vocabulary, hesitation patterns)
4. **Gets LeMUR analysis** (AssemblyAI's AI analysis)
5. **Generates teacher feedback** (talk time, vocabulary calibration, pacing)
6. **Sends results to GitEnglishHub** via API

That's it. It does NOT:
- ❌ Store anything in databases
- ❌ Create student cards
- ❌ Run a website

---

## Quick Start

```bash
# Set up environment
cp .env.example .env
# Edit .env with your keys

# Install dependencies  
pip install -r requirements.txt

# Process an audio file
python ingest_audio.py

# OR record live
python main.py
```

---

## Required Environment Variables

```bash
# AssemblyAI (for transcription)
ASSEMBLYAI_API_KEY=your_key

# GitEnglishHub connection (where results go)
MCP_SECRET=must_match_gitenglishhub
GITENGLISH_API_BASE=https://www.gitenglish.com
```

The `MCP_SECRET` MUST be the same in GitEnglishHub's environment.

---

## Analysis Output

After processing, the session analysis includes:

### Student Metrics
| Metric | Description |
|--------|-------------|
| `speaking_rate` | Average/min/max words per minute |
| `pauses` | Total pauses, long pauses (>1s), average duration |
| `complexity_basic` | Total words, unique words, vocabulary diversity |
| `fillers` | Count of um, uh, like, you know, etc. |
| `hesitation_patterns` | Words that precede long pauses (avoidance detection) |
| `vocabulary_analysis` | Unique lemmas, overlap with teacher |

### Teacher Metrics
Same metrics as student, allowing direct comparison.

### Comparison (Side-by-Side)
| Metric | What It Shows |
|--------|---------------|
| `talk_time_ratio` | Student vs Teacher word count & percentages |
| `vocabulary_calibration` | Teacher:Student unique words ratio |
| `speaking_rate_comparison` | WPM difference |
| `pause_comparison` | Who pauses more |
| `turn_balance` | Who takes more turns |

### Teacher Feedback
Actionable feedback with type (positive/warning/info):
- **Talk Time**: "Student spoke 45% - ideal range"
- **Vocabulary Level**: "Your vocabulary is 1.8x the student's - perfect for i+1"
- **Speaking Speed**: "Well-paced! Within 20 WPM of student"
- **Turn Taking**: "Good conversational flow"
- **Overall Score**: 1-10 teaching effectiveness score

### Hesitation Pattern Detection
Identifies words that precede long pauses (>800ms):
```json
{
  "total_hesitations": 12,
  "frequent_hesitation_words": {"the": 3, "because": 2, "actually": 2},
  "details": [{"word": "because", "pause_duration_ms": 1200, "confidence": 0.92}]
}
```

This helps identify vocabulary the student may be avoiding or struggling with.

---

## The Data Flow

```
   Audio (from mic or file)
           │
           ▼
   Semantic Surfer sends to AssemblyAI
   (with speaker_labels=True for diarization)
           │
           ▼
   AssemblyAI transcribes + identifies speakers
           │
           ▼
   Local Analysis runs (session_analyzer.py)
   - Student metrics
   - Teacher metrics  
   - Comparison
   - Hesitation patterns
   - Teacher feedback
           │
           ▼
   LeMUR Analysis runs (lemur_query.py)
   - Phonology, Lexis, Syntax, Pragmatics
   - Tutor feedback on teaching approach
           │
           ▼
   Semantic Surfer sends to GitEnglishHub API
           │
           ▼
   GitEnglishHub stores in Sanity/Supabase
           │
           ▼
   Student sees Post-Lesson Card
   Teacher sees feedback dashboard
```

---

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Live session recording |
| `ingest_audio.py` | File-based audio processing |
| `analyzers/session_analyzer.py` | Local analysis engine (Fast & Free) |
| `analyzers/lemur_query.py` | LeMUR AI analysis (Paid) |

---

## If Something Breaks

- **Transcription not working?** → Check AssemblyAI API key
- **Data not appearing in GitEnglishHub?** → Check MCP_SECRET matches
- **Website broken?** → That's GitEnglishHub, not this tool
- **Analysis empty?** → Check speaker_map in session JSON

---

## For Full Platform Documentation

See: **`gitenglishhub/ARCHITECTURE.md`**

---

*This is a transcription & analysis tool. It is not a platform. It is not GitEnglishHub.*
