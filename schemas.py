from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

# --- 1. The 4 Real Linguistic Categories (SLA Domains) ---
class AnalysisCategory(str, Enum):
    PHONOLOGY = "Phonology"       # Pronunciation, Intonation, Stress
    LEXIS = "Lexis"               # Vocabulary, Collocations, Formulaic Language
    SYNTAX = "Syntax"             # Grammar, Morphology, Sentence Structure
    PRAGMATICS = "Pragmatics"     # Discourse, Coherence, Register, Appropriateness

# --- 2. Analysis Payload ---
class LanguageFeedback(BaseModel):
    category: AnalysisCategory = Field(..., description="The linguistic category of the issue.")
    suggested_correction: str = Field(..., description="The natural, corrected version of the sentence.", alias="suggestedCorrection")
    explanation: str = Field(..., description="A concise explanation of the error (max 2 sentences).")
    detected_trigger: Optional[str] = Field(None, description="The specific word or phrase that triggered this feedback.")

# --- 3. Turn Data ---
class Turn(BaseModel):
    turn_order: int
    transcript: str
    speaker: str
    timestamp: Optional[str] = None
    analysis: Optional[LanguageFeedback] = None

    class Config:
        populate_by_name = True
