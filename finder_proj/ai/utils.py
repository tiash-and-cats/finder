import numpy as np
import pickle

_model = None
_embeddings = None
_docs = None

def get_model():
    global _model
    if _model is None:
        print("Loading embedding model...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return _model

def get_index_data():
    global _embeddings, _docs
    if _embeddings is None or _docs is None:
        print("Loading precomputed embeddings and docs...")
        _embeddings = np.load("ai/embeddings.npy")
        with open("ai/docs.pkl", "rb") as f:
            _docs = pickle.load(f)
    return _embeddings, _docs

def get_similar_docs(query, top_k=3):
    model = get_model()
    embeddings, docs = get_index_data()

    query_vec = model.encode([query], convert_to_numpy=True)[0]
    scores = embeddings @ query_vec  # cosine similarity
    top_indices = scores.argsort()[-top_k:][::-1]
    return [docs[i] for i in top_indices]

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

_lm_tokenizer = None
_lm_model = None

def get_lm():
    global _lm_tokenizer, _lm_model
    if _lm_model is None:
        print("Loading local language model...")
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"  # or another small model that fits
        _lm_tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        _lm_model = AutoModelForCausalLM.from_pretrained(model_name)
    return _lm_tokenizer, _lm_model

def generate_reply(query, docs, history=None):
    context = "\n".join(f"- {doc}" for doc in docs)
    chat_log = ""
    if history:
        chat_log = "\n".join(f"{msg['role'].capitalize()}: {msg['content']}" for msg in history)

    prompt = f"""You are a helpful assistant.
Context:
{context}

{chat_log}
User: {query}
Assistant:"""

    tokenizer, model = get_lm()
    input_ids = tokenizer.encode(prompt, return_tensors="pt")
    print(input_ids.shape)  # should be (1, sequence_length)
    output = model.generate(input_ids, max_new_tokens=32, do_sample=True, temperature=0.7)
    response = tokenizer.decode(output[0], skip_special_tokens=True)

    # Trim the response to just the assistant's reply
    return response.split("Assistant:")[-1].strip()

def load_embedding_model():
    try:
        get_model()
    except Exception as e:
        print("Failed to load embedding model:", e)

def load_language_model():
    try:
        get_lm()
    except Exception as e:
        print("Failed to load language model:", e)