import re

def clean_word(text):
    return re.sub(r'[^\w\s]', '', text)

test_cases = [
    ("Hello,", "Hello"),
    ("world!", "world"),
    ("What's", "Whats"),
    ("yes.", "yes"),
    ("word", "word"),
    ("...um...", "um")
]

print("Running Regex Cleaning Test:")
print("-" * 30)
for input_text, expected in test_cases:
    cleaned = clean_word(input_text)
    status = "✅" if cleaned == expected else "❌"
    print(f"Input: '{input_text:<10}' -> Output: '{cleaned:<10}' | Expected: '{expected:<10}' {status}")
