
import os
from django.apps import AppConfig
import threading
from .utils import load_embedding_model, load_language_model

class AiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai'

    def ready(self):
        # Prevent reloading during the initial autoreloader fork
        if os.environ.get("RUN_MAIN") != "true":
            return

        threading.Thread(target=load_embedding_model, daemon=True).start()
        threading.Thread(target=load_language_model, daemon=True).start()
        
_ = """

import os
from django.apps import AppConfig
from .utils import get_model, get_lm

class AiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai'

    def ready(self):
        if os.environ.get("RUN_MAIN") != "true":
            return

        print("==> Loading models directly to catch crashes.")
        get_model()
        get_lm()
""" 