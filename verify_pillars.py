from analyzers.lexical_engine import LexicalEngine
from analyzers.sentence_chunker import chunk_transcript

def test_pillars():
    print("--- Pillar 1: LexicalEngine (with Cognitive Effort) ---")
    engine = LexicalEngine()
    
    # Test cases: Exact, Lemma, Fuzzy (Cognitive Effort), and Noise
    test_words = [
        {"text": "running", "confidence": 1.0},       
        {"text": "beautifull", "confidence": 1.0},    
        {"text": "accomodation", "confidence": 1.0},  
        {"text": "xyz123abc", "confidence": 1.0},    
        {"text": "casa", "confidence": 1.0}          
    ]
    
    results = engine.analyze_production(test_words)
    print(f"Reconstructed: {results['raw_text']}")
    for word in results['words']:
        print(f"- {word['text']} -> Lemma: {word['lemma']} (POS: {word.get('pos')}) (Whitelisted: {word['is_whitelisted']}, Academic: {word['is_academic']})")

    print("\n--- Pillar 2: Sentence-Aware Chunker ---")
    context_text = "This is the first sentence. This is the second sentence. I want to see overlap."
    chunks = chunk_transcript(context_text, max_chunk_chars=50, sentence_overlap=1)
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk}")

if __name__ == "__main__":
    test_pillars()
