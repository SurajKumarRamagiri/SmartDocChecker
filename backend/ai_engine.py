from transformers import pipeline
from sentence_transformers import SentenceTransformer
import spacy

# Load models (in production, use caching and async loading)
contradiction_model = pipeline('text-classification', model='xlm-roberta-base')
similarity_model = SentenceTransformer('paraphrase-xlm-r-multilingual-v1')
nlp = spacy.load('en_core_web_sm')

def detect_contradictions(texts):
    # Batch process texts for contradiction detection
    results = contradiction_model(texts)
    return results

def calculate_similarity(sent1, sent2):
    # Semantic similarity
    return similarity_model.similarity(sent1, sent2)

def extract_entities(text):
    doc = nlp(text)
    return [(ent.text, ent.label_) for ent in doc.ents]
