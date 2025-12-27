
import asyncio
import os
import json
import sys
from pathlib import Path

# Setup paths
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(WORKSPACE_ROOT))

from AssemblyAIv2.analyzers.llm_gateway import generate_analysis

async def main():
    # Paths to Francisco's session data
    session_dir = Path("/Users/safeSpacesBro/AssemblyAIv2/.session_captures/Francisco/2025-12-26")
    transcript_file = session_dir / "12-45-00_Francisco_diarized.txt"
    guru_prompt_file = Path("/Users/safeSpacesBro/AssemblyAIv2/UNIVERSAL_GURU_PROMPT.txt")
    output_file = session_dir / "12-45-00_Francisco_GURU_REPORT.json"

    print(f"🚀 Starting Guru Analysis for Francisco...")

    if not transcript_file.exists():
        print(f"❌ Transcript not found: {transcript_file}")
        return
    if not guru_prompt_file.exists():
        print(f"❌ Guru prompt not found: {guru_prompt_file}")
        return

    # Read inputs
    with open(transcript_file, "r") as f:
        transcript_text = f.read()
    
    with open(guru_prompt_file, "r") as f:
        system_prompt = f.read()

    # Prepare user message
    user_message = f"Please analyze the following transcript for Francisco:\n\n{transcript_text}"

    # Run analysis
    # ASSEMBLYAI_API_KEY should be in environment
    try:
        result = await generate_analysis(
            system_prompt=system_prompt,
            user_message=user_message,
            model="gemini-3-flash-preview"
        )

        if result:
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"✅ Guru Analysis Complete. Saved to: {output_file}")
            print("\nSummary Preview:")
            print(result.get("session_summary", "No summary provided"))
        else:
            print("❌ Guru Analysis failed (no result returned)")

    except Exception as e:
        print(f"💥 Guru Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
