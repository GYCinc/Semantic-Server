
import asyncio
import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Setup paths for GitEnglishHub and AssemblyAIv2
PROJECT_ROOT = Path("/Users/safeSpacesBro/gitenglishhub")
AAI_ROOT = Path("/Users/safeSpacesBro/AssemblyAIv2")
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(AAI_ROOT))

# Import the 4-phase engine and classifier
from lib.processing.session_extract import generateSessionExtract
from lib.processing.classifier import extractPhenomena, extractActionItems, extractTeacherReflection

async def run_francisco_pipeline():
    print("🚀 INITIALIZING FRANCISCO SUPREME PIPELINE...")
    
    # 1. LOAD FRANCISCO DATA
    session_dir = AAI_ROOT / ".session_captures/Francisco/2025-12-26"
    transcript_path = session_dir / "12-45-00_Francisco_diarized.txt"
    words_path = session_dir / "12-45-00_Francisco_words.json"
    
    if not transcript_path.exists():
        print(f"❌ Missing transcript: {transcript_path}")
        return

    with open(transcript_path, "r") as f:
        transcript_text = f.read()
    
    words = []
    if words_path.exists():
        with open(words_path, "r") as f:
            words = json.load(f)

    # 2. PHASE A: PETTY DANTIC (Linguist Loop - 4 Phase)
    print("🧠 PHASE A: RUNNING PETTY DANTIC LINGUIST LOOP (4-PHASES)...")
    # We use generateSessionExtract which implements the 4-phase sequential execution
    petty_result = await generateSessionExtract({
        "studentName": "Francisco",
        "sessionDate": "2025-12-26",
        "rawNotes": "Focus: Business English, Confidence, Past Tense vs Present Perfect.",
        "deterministicErrors": [] # Will be populated by the internal detector if we passed words
    })
    
    # 3. PHASE B: FRANCISCO MINI-GURU (The "Boss MF" Persona)
    print("🦅 PHASE B: AWAKENING FRANCISCO MINI-GURU (BOSS MF)...")
    
    # Load the Boss MF prompt and specialize it for Francisco
    guru_prompt_path = AAI_ROOT / "UNIVERSAL_GURU_PROMPT.txt"
    with open(guru_prompt_path, "r") as f:
        guru_prompt = f.read().replace("Eren", "Francisco")
    
    # Run the Guru pass using the Petty Dantic baseline
    guru_result = await extractPhenomena(
        text=transcript_text,
        studentId="francisco-uuid", # Hypothetical, will trigger Guru context if matched
        words=words
    )
    
    actions = await extractActionItems(transcript_text)
    reflection = await extractTeacherReflection(transcript_text)

    # 4. AGGREGATE FINAL GOD-TIER JSON
    final_package = {
        "metadata": {
            "student": "Francisco",
            "date": "2025-12-26",
            "version": "v4.6.0-Sovereign",
            "pipeline": "PettyDantic -> MiniGuru"
        },
        "session_extract": petty_result,
        "guru_analysis": guru_result,
        "action_items": actions,
        "teacher_reflection": reflection,
        "timestamp": datetime.now().isoformat()
    }

    # 5. HANDOFF TO INBOX (Policy Compliance)
    inbox_path = AAI_ROOT / "admin_inbox" / "2025-12-26_Francisco_HANDOFF.json"
    with open(inbox_path, "w") as f:
        json.dump(final_package, f, indent=2)
    
    print(f"✅ SUCCESS: Handoff package created at {inbox_path}")
    print(f"📝 Summary: {guru_result.get('summary', 'No summary')[:200]}...")

if __name__ == "__main__":
    # Ensure API Key is available
    if not os.getenv("ASSEMBLYAI_API_KEY"):
        os.environ["ASSEMBLYAI_API_KEY"] = "b2fac99657a248c8ae6622442d64587a"
    
    asyncio.run(run_francisco_pipeline())
