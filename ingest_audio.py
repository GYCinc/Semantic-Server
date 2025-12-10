import os
import sys
import json
import asyncio
import logging
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import assemblyai as aai
import httpx  # Added for GitEnglishHub API
from supabase import create_client, Client

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IngestAudio")

# --- Load Environment ---
load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
AAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# GitEnglishHub Integration (The proper pipeline!)
GITENGLISH_API_BASE = os.getenv("GITENGLISH_API_BASE", "https://www.gitenglish.com")
MCP_SECRET = os.getenv("MCP_SECRET")

if not AAI_API_KEY:
    logger.error("❌ ASSEMBLYAI_API_KEY not found in environment.")
    sys.exit(1)

aai.settings.api_key = AAI_API_KEY

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client initialized (for student lookup only)")
    except Exception as e:
        logger.warning(f"⚠️ Supabase init failed: {e} - Will use GitEnglishHub for student lookup")
else:
    logger.info("ℹ️ Supabase not configured - Using GitEnglishHub API for everything")

# Check GitEnglishHub is configured
if not MCP_SECRET:
    logger.warning("⚠️ MCP_SECRET not set! GitEnglishHub API calls will fail.")


# --- Helper Functions (Reused/Adapted from main.py) ---

async def send_to_gitenglish(action: str, student_id: str, params: dict) -> dict:
    """
    Send data to GitEnglishHub's Petty Dantic API.
    This is THE pipeline - Semantic Surfer sends raw data, GitEnglish handles all DB logic.
    """
    if not MCP_SECRET:
        logger.error("❌ MCP_SECRET not set! Cannot call GitEnglishHub API.")
        return {"success": False, "error": "MCP_SECRET not configured"}
    
    url = f"{GITENGLISH_API_BASE}/api/mcp"
    headers = {
        "Authorization": f"Bearer {MCP_SECRET}",
        "Content-Type": "application/json"
    }
    payload = {
        "action": action,
        "studentId": student_id,
        "params": params
    }
    
    logger.info(f"📤 Calling GitEnglishHub: {action}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ GitEnglishHub response: {result.get('success', 'unknown')}")
                return result
            else:
                logger.error(f"❌ GitEnglishHub error ({response.status_code}): {response.text}")
                return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        logger.error(f"❌ Failed to call GitEnglishHub: {e}")
        return {"success": False, "error": str(e)}


def get_student_id(name):
    """Find student ID by name (username or first_name) - uses Supabase for local lookup"""
    if not supabase:
        logger.warning("Supabase not available - returning name for GitEnglishHub to resolve")
        return name  # GitEnglishHub can resolve by name
    try:
        # Try exact username match
        res = supabase.table("students").select("id").eq("username", name).execute()
        if res.data:
            return res.data[0]['id']
        
        # Try first name match
        res = supabase.table("students").select("id").eq("first_name", name).execute()
        if res.data:
            return res.data[0]['id']
            
        return name  # Let GitEnglishHub resolve
    except Exception as e:
        logger.error(f"Error finding student ID: {e}")
        return name

async def perform_batch_diarization(audio_path):
    """
    Uploads audio to AssemblyAI Batch API for accurate diarization.
    Returns the transcript object.
    """
    if not os.path.exists(audio_path):
        logger.error(f"❌ Audio file not found: {audio_path}")
        return None

    logger.info("🔄 Starting Batch Diarization...")
    try:
        transcriber = aai.Transcriber()

        # --- DUAL-PASS STRATEGY ---
        # Pass 1: Raw (No punctuation/formatting) - To capture student errors exactly as spoken
        print(f"🎙️  Pass 1: Raw Transcription (Capturing errors)...")
        config_raw = aai.TranscriptionConfig(
            punctuate=False,
            format_text=False,
            speech_model='universal'  # Universal for raw batch
        )
        transcript_raw = transcriber.transcribe(audio_path, config_raw)
        
        if transcript_raw.status == "error":
             print(f"❌ Raw transcription failed: {transcript_raw.error}")
             return None, None
             
        # Pass 2: Diarized (With punctuation/speakers) - To identify who spoke
        print(f"👥 Pass 2: Diarization (Identifying speakers)...")
        config_diarized = aai.TranscriptionConfig(
            speaker_labels=True,
            speakers_expected=2,
            punctuate=True, # Required for diarization
            format_text=False, # Keep fillers
            speech_model='slam-1'  # slam-1 for diarized
        )
        transcript_diarized = transcriber.transcribe(audio_path, config_diarized)
        
        if transcript_diarized.status == "error":
            print(f"❌ Diarized transcription failed: {transcript_diarized.error}")
            return None, None

        # --- MERGE: Map Raw Words to Speakers ---
        # We use the timestamps from the Raw words to find which Speaker Turn they fall into
        print(f"🔄 Merging Raw Words with Speaker Labels...")
        
        # 1. Build an Interval Tree or simple list of (start, end, speaker) from Diarized
        speaker_intervals = []
        for turn in transcript_diarized.utterances:
            speaker_intervals.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': turn.speaker
            })
            
        # 2. Assign speaker to each Raw word
        # Determine Student Speaker (A or B)
        # Heuristic: Teacher usually speaks more? Or prompting user? 
        # For now, let's assume 'B' is student or ask. 
        # Actually, the user prompt logic happens later. We just need to label them.
        
        # We will reconstruct "turns" for the existing logic to consume, 
        # but specifically using RAW words.
        
        # Let's map raw words to their speakers
        raw_words_with_speaker = []
        for word in transcript_raw.words:
            # Find speaker
            word_speaker = 'Unknown'
            w_center = word.start + (word.end - word.start) / 2
            
            for interval in speaker_intervals:
                if interval['start'] <= w_center <= interval['end']:
                    word_speaker = interval['speaker']
                    break
            
            raw_words_with_speaker.append({
                'text': word.text, # Raw text!
                'start': word.start,
                'end': word.end,
                'confidence': word.confidence,
                'speaker': word_speaker
            })
            
        # Re-group into turns for the existing logic
        # The existing logic expects `student_turns`.
        
        # Identify Student Speaker Label
        # We can reuse the existing logic's assumption or ask. 
        # The existing logic asks "Enter Student Name". 
        # But we need to know WHICH label is the student.
        # Usually: A=Tutor, B=Student (or detected).
        
        # Let's group by speaker to match `student_turns` structure
        all_turns = []
        current_turn = None
        
        for w in raw_words_with_speaker:
            if current_turn and current_turn['speaker'] == w['speaker']:
                current_turn['words'].append(w)
                current_turn['transcript'] += " " + w['text'] # Changed 'text' to 'transcript' to match original structure
                current_turn['end'] = w['end'] # Update end time
            else:
                if current_turn:
                    all_turns.append(current_turn)
                current_turn = {
                    'speaker': w['speaker'],
                    'transcript': w['text'], # Changed 'text' to 'transcript'
                    'start': w['start'],
                    'end': w['end'],
                    'confidence': w['confidence'], # Assuming turn confidence is word confidence for now
                    'words': [w]
                }
        if current_turn:
            all_turns.append(current_turn)

        # Now filter for STUDENT ONLY turns
        # We'll need the logic to identify the student label
        # (This logic was lower down, we need to adapt it)
        
        # Determine student label (simple heuristic: Speaker B is usually student, or A if B is missing?)
        # Valid assumption for now: B is student.
        student_label = 'B' 
        
        # Return ALL turns (Teacher + Student) so we can save the full session
        print(f"✅ Diarization and Merge Complete. Duration: {transcript_diarized.audio_duration}s")
        return all_turns, transcript_diarized.audio_duration

    except Exception as e:
        logger.error(f"❌ Diarization error: {e}")
        return None, None

async def process_and_upload(audio_path, student_name, notes=""):
    logger.info(f"🚀 Processing: {audio_path} for {student_name}")
    
    # 1. Validate Student
    student_id = get_student_id(student_name)
    if not student_id:
        logger.error(f"❌ Student '{student_name}' not found in Supabase.")
        return
    logger.info(f"✅ Found Student ID: {student_id}")

    # 2. Diarize (Dual-Pass)
    all_turns, duration = await perform_batch_diarization(audio_path)
    if all_turns is None or duration is None:
        logger.error("❌ Diarization failed or returned no data.")
        return

    # 3. Construct Session Data
    session_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    logger.info(f"✅ Diarization Complete. Duration: {duration}s")
    
    # Map speakers (Simple heuristic: Speaker A = Aaron, B = Student)
    speaker_map = {
        "A": "Aaron",
        "B": student_name
    }
    
    turns = []
    student_turns = []
    
    for turn in all_turns:
        speaker_label = turn['speaker']
        speaker_name = speaker_map.get(speaker_label, speaker_label)
        
        # Construct turn object (using dict access for 'turn')
        turn_obj = {
            "speaker": speaker_name,
            "transcript": turn['transcript'],
            "start": turn['start'],
            "end": turn['end'],
            "confidence": turn['confidence'],
            "words": [{"text": w['text'], "start": w['start'], "end": w['end'], "confidence": w['confidence']} for w in turn['words']]
        }
        turns.append(turn_obj)
        
        # Identify Student Turns (Assuming B is student)
        if speaker_label == 'B':
            student_turns.append(turn_obj)

    # 4. Analyze Notes (LLM)
    import httpx
    notes_analysis = None
    if notes:
        logger.info("📝 Analyzing notes with LLM...")
        try:
            prompt = f"""Analyze these tutor notes from an ESL class session. Extract:
1. Key teaching moments or observations
2. Action items for the tutor (things to look up, send, prepare)
3. Student progress indicators
4. Areas of concern

Notes: {notes}

Provide a structured JSON response with: teaching_moments, action_items, progress_notes, concerns"""
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://llm-gateway.assemblyai.com/v1/chat/completions",
                    headers={"Authorization": AAI_API_KEY},
                    json={
                        "model": "anthropic/claude-3-5-sonnet",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    notes_analysis = {
                        "raw_notes": notes,
                        "llm_analysis": result['choices'][0]['message']['content']
                    }
                    logger.info("✅ Notes analyzed successfully")
        except Exception as e:
            logger.warning(f"Note analysis failed: {e}")
            notes_analysis = {"raw_notes": notes}

    # ============================================================
    # STEP 2.5: LeMUR LINGUISTIC ANALYSIS (The "Guru")
    # ============================================================
    logger.info("🦁 Sending transcript to LeMUR for Deep Linguistic Analysis...")

    lemur_analysis = None
    extracted_phenomena = []

    try:
        # Construct the "Agent Prompt"
        # We process the FULL transcript (Teacher + Student) to give context,
        # but ask the LLM to focus on the Student's errors.
        
        # Format transcript for LeMUR
        full_transcript_text = "\n".join([f"{t['speaker']}: {t['transcript']}" for t in turns])
        
        system_prompt = f"""You are an Expert Applied Linguist and ESL Analyst. 
your task is to analyze the speech of the student ("{student_name}") in the following transcript.
The other speaker ("Aaron" or "Tutor") is the teacher.

Analyze the student's speech for errors and patterns across these 4 domains:
1. PHONOLOGY: Pronunciation issues, stress errors, intonation problems (if inferable or marked in text), and fluency breaks.
2. LEXIS: Vocabulary choices, potential false friends, collocation errors, phrasal verb misuse.
3. SYNTAX: Grammatical errors, sentence structure issues, tense consistency.
4. PRAGMATICS: Register appropriateness, cohesiveness, turn-taking.

For each error or notable pattern found:
- Quote the specific text (Context).
- Categorize it into one of the 4 domains.
- Provide a correction or better alternative.
- Explain WHY it is an error (brief linguistic explanation).

OUTPUT FORMAT:
Return ONLY a valid JSON object with this structure:
{{
  "summary": "Brief executive summary of student performance...",
  "errors": [
    {{
      "domain": "Syntax",
      "error_type": "Tense Consistency",
      "text": "I have went to the store",
      "correction": "I went to the store (or I have gone)",
      "explanation": "Confusion between past simple and present perfect/participle."
    }},
    ...
  ],
  "strengths": ["list of strengths..."],
  "cefr_estimate": "B1/B2 etc."
}}
"""
        
        # Call LeMUR
        # Note: We use the 'transcript_ids' param to let LeMUR access the full AAI transcript features
        # But we also pass the 'input_text' context via the prompt if we want specific formatting.
        # Actually, best practice with AAI SDK is `transcript.lemur.task(prompt, final_model=...)`
        
        # We don't have the 'transcript' object from batch (we do! `transcript_diarized`).
        # But `process_and_upload` receives `audio_path`.
        # Wait, `perform_batch_diarization` returns `all_turns`, not the transcript object.
        # I need to fetch the transcript object or pass it back.
        # Refactoring `perform_batch_diarization` to return transcript input ID?
        # Or just pass the text to LeMUR task via context? Passing text is easier/flexible.
        
        lemur_output = aai.Lemur().task(
            prompt=system_prompt,
            input_text=full_transcript_text,
            final_model=aai.LemurModel.claude3_5_sonnet # High intelligence model
        )
        
        logger.info(f"🦁 LeMUR Response received. Tokens: {lemur_output.usage}")
        
        # Parse JSON
        try:
            # Clean potential markdown fences
            clean_response = lemur_output.response.replace("```json", "").replace("```", "").strip()
            lemur_data = json.loads(clean_response)
            
            lemur_analysis = lemur_data.get('summary')
            
            # Convert LeMUR errors to our ExtractedPhenomena format
            for err in lemur_data.get('errors', []):
                extracted_phenomena.append({
                    "item": err.get('text'),
                    "category": err.get('domain'), # Will be cross-referenced later
                    "context": f"{err.get('text')} -> {err.get('correction')}",
                    "explanation": err.get('explanation'),
                    "correction": err.get('correction'),
                    "confidence": 0.9 # High confidence from LeMUR
                })
                
            logger.info(f"✅ Extracted {len(extracted_phenomena)} linguistic phenomena")
            
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse LeMUR JSON response")
            lemur_analysis = lemur_output.response # Fallback to raw text

    except Exception as e:
        logger.error(f"❌ LeMUR Task Failed: {e}")

    # Build the transcript text for the analysis report (Legacy format)
    student_turns = [t for t in turns if t["speaker"] != "Aaron"]
    transcript_text = "\n".join([
        f"{t['speaker']}: {t['transcript']}"
        for t in turns
    ])
    
    # Calculate basic metrics
    total_words = sum(len(t.get('words', [])) for t in student_turns)
    
    # Build analysis report
    analysis_report = f"""Session Analysis
Duration: {duration}s
Student Words: {total_words}
Turns: {len(student_turns)}

-- LeMUR Summary --
{lemur_analysis if lemur_analysis else 'No analysis available.'}

-- Teaching Notes Analysis --
{notes_analysis.get('llm_analysis', '') if notes_analysis else ''}
"""

    # ============================================================
    # STEP 1: CREATE SESSION IN GITENGLISHHUB (For Curation UI)
    # This creates the student_sessions record so teacher can curate
    # ============================================================
    logger.info("📤 Creating session via Petty Dantic API...")
    
    session_result = await send_to_gitenglish(
        action='ingest.createSession',
        student_id=student_id,
        params={
            'turns': turns,  # Full turns data with words
            'transcriptText': transcript_text,
            'sessionDate': timestamp,
            'duration': duration,
            'lemurAnalysis': lemur_analysis,
            'extractedPhenomena': extracted_phenomena
        }
    )
    
    if session_result.get('success'):
        session_id = session_result.get('sessionId')
        logger.info(f"✅ Session created: {session_id}")
        logger.info(f"   Pending words: {session_result.get('pendingWords', 0)}")
    else:
        logger.error(f"❌ Session creation failed: {session_result.get('error')}")
        logger.error("   Check MCP_SECRET matches between systems")
        return


    # ============================================================
    # SEND STUDENT WORDS TO CORPUS (Via API)
    # Extracts words and sends them to GitEnglishHub to handle storage
    # ============================================================
    logger.info("📚 Sending student words to corpus via API...")
    
    corpus_entries = []
    word_position = 0
    
    import re
    
    for turn in student_turns:
        words = turn.get('words', [])
        for word_data in words:
            raw_text = word_data.get('text', '').strip()
            # Clean punctuation from the word (e.g. "Hello," -> "Hello")
            word_text = re.sub(r'[^\w\s]', '', raw_text)
            
            if word_text and len(word_text) > 1:  # Skip single chars and empty strings
                start_ms = word_data.get('start', 0)
                end_ms = word_data.get('end', 0)
                
                corpus_entries.append({
                    'word_text': word_text,
                    'word_position': word_position,
                    'word_start_ms': start_ms,
                    'word_end_ms': end_ms,
                    'word_duration_ms': end_ms - start_ms,
                    'word_confidence': word_data.get('confidence', 0)
                })
                word_position += 1
    
    # Send corpus entries in batches
    batch_size = 25
    for i in range(0, len(corpus_entries), batch_size):
        batch = corpus_entries[i:i+batch_size]
        
        corpus_result = await send_to_gitenglish(
            action='schema.addToCorpus',
            student_id=student_id,
            params={
                'source': 'semantic_surfer',
                'words': batch, # Sending RAW word data
                'metadata': {
                    'session_id': session_id,
                    'session_date': timestamp,
                    'batch_index': i // batch_size
                }
            }
        )
        
        if corpus_result.get('success'):
            logger.info(f"   ✅ Batch {i // batch_size + 1}: {len(batch)} words sent")
        else:
            logger.warning(f"   ⚠️ Batch {i // batch_size + 1} failed: {corpus_result.get('error')}")

    logger.info("🎉 Ingestion Complete!")


# --- Main Interactive Loop ---
async def main():
    print("\n" + "="*60)
    print("🎧 AUDIO INGESTION TOOL")
    print("="*60)
    
    # Get Audio File
    while True:
        audio_path = input("\n📁 Drag & Drop Audio File (or type path): ").strip().replace("'", "").replace('"', "")
        if os.path.exists(audio_path):
            break
        print("❌ File not found. Try again.")

    # Get Student
    print("\n🎓 Select Student:")
    # Fetch students
    try:
        res = supabase.table("students").select("username, first_name").execute()
        students = [s.get('username') for s in res.data]
        for i, name in enumerate(students):
            print(f"  [{i+1}] {name}")
    except:
        students = []
    
    student_choice = input(f"\nEnter number or name: ").strip()
    student_name = None
    
    if student_choice.isdigit():
        idx = int(student_choice) - 1
        if 0 <= idx < len(students):
            student_name = students[idx]
    
    if not student_name:
        student_name = student_choice # Fallback to raw input

    if not student_name:
        print("❌ Invalid student.")
        return

    # Get Notes
    print("\n📝 Tutor Notes (Optional):")
    notes = input("Enter notes (or press Enter to skip): ").strip()

    await process_and_upload(audio_path, student_name, notes)

if __name__ == "__main__":
    asyncio.run(main())
