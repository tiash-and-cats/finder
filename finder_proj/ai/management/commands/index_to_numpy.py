# management/commands/index_to_numpy.py
from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
from api.models import Indexed
import numpy as np
import pickle

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        model = SentenceTransformer("all-MiniLM-L6-v2")
        docs = Indexed.objects.values_list("content", flat=True)
        docs = [d.replace("\n", " ").strip()[:1000] for d in docs]  # trim to 1k chars
        embeddings = model.encode(docs, convert_to_numpy=True)

        np.save("ai/embeddings.npy", embeddings)
        with open("ai/docs.pkl", "wb") as f:
            pickle.dump(list(docs), f)

        self.stdout.write(self.style.SUCCESS("Saved embeddings and docs!"))