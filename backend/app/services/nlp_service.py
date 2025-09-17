# In backend/app/services/nlp_service.py

import spacy
from collections import Counter
from typing import List

# Load the spaCy model once when the module is imported.
# This is efficient as it avoids reloading the model on every function call.
try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    print(
        "Downloading 'en_core_web_lg' model...\n"
        "This may take a moment. Please run the following command if it fails:\n"
        "poetry run python -m spacy download en_core_web_lg"
    )
    from spacy.cli import download
    download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

def extract_entities_from_text(text: str, top_n: int = 20) -> List[str]:
    """
    Extracts named entities from a given text using spaCy, counts their
    frequency, and returns the most common ones.

    This function focuses on entities that provide strong semantic context for
    SEO, such as organizations, people, and products, while filtering out
    more generic or noisy entities like dates and numbers.

    Args:
        text: The input text to analyze.
        top_n: The number of top entities to return.

    Returns:
        A list of the most frequent and relevant named entities.
    """
    if not text:
        return []
        
    doc = nlp(text)
    
    # We are interested in specific entity types that add the most SEO value.
    # Excluded types like DATE, CARDINAL, etc., are often just noise.
    allowed_entity_labels = [
        "PERSON",  # People, characters
        "ORG",     # Companies, agencies, institutions
        "GPE",     # Geopolitical entities (countries, cities, states)
        "PRODUCT", # Objects, vehicles, foods, etc. (not services)
        "WORK_OF_ART", # Titles of books, songs, etc.
        "EVENT",   # Named hurricanes, battles, wars, sports events, etc.
        "FAC"      # Buildings, airports, highways, bridges, etc.
    ]
    
    entities = [
        ent.text.strip() for ent in doc.ents 
        if ent.label_ in allowed_entity_labels and len(ent.text.strip()) > 2
    ]
    
    # Count the frequency of each entity
    entity_counts = Counter(entities)
    
    # Get the most common entities
    most_common_entities = [entity for entity, count in entity_counts.most_common(top_n)]
    
    print(f"Extracted Top {len(most_common_entities)} Entities: {most_common_entities}")
    return most_common_entities