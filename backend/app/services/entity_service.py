import spacy
from collections import Counter

# Load the spaCy model once when the module is imported for efficiency.
try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    print("spaCy model 'en_core_web_lg' not found. Please run 'poetry run python -m spacy download en_core_web_lg'")
    nlp = None

# Exclude entity types that are not relevant for topical authority.
EXCLUDED_ENTITY_TYPES = ["DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL", "LANGUAGE"]

def extract_entities_from_corpus(corpus: str, top_n: int = 20) -> list[str]:
    """
    Analyzes a text corpus using spaCy to extract the most relevant entities.
    """
    if not nlp:
        return []

    print("--- 🧠 Performing local entity analysis with spaCy ---")
    doc = nlp(corpus)
    
    entities = [
        ent.text.strip() for ent in doc.ents 
        if ent.label_ not in EXCLUDED_ENTITY_TYPES and len(ent.text.strip()) > 2
    ]
    
    # Return the most frequently mentioned entities.
    most_common_entities = [entity for entity, count in Counter(entities).most_common(top_n)]
    
    return most_common_entities
