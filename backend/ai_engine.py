from transformers import XLMRobertaTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer, util
import spacy

# Use slow tokenizer directly
xlm_tokenizer = XLMRobertaTokenizer.from_pretrained("joeddav/xlm-roberta-large-xnli")
xlm_model = AutoModelForSequenceClassification.from_pretrained("joeddav/xlm-roberta-large-xnli")

sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
nlp = spacy.load("en_core_web_sm")

def detect_contradiction(text1, text2):
    inputs = xlm_tokenizer(text1, text2, return_tensors="pt", truncation=True)
    outputs = xlm_model(**inputs)
    logits = outputs.logits.detach().numpy()[0]
    # label 0: entailment, 1: neutral, 2: contradiction
    contradiction_score = float(logits[2])
    return contradiction_score

def semantic_similarity(text1, text2):
    emb1 = sbert_model.encode(text1, convert_to_tensor=True)
    emb2 = sbert_model.encode(text2, convert_to_tensor=True)
    score = util.pytorch_cos_sim(emb1, emb2).item()
    return score

def extract_entities(text):
    doc = nlp(text)
    return [(ent.text, ent.label_) for ent in doc.ents]
