from api.ai.ports.sentiment_analyzer import SentimentAnalyzer
import os
from huggingface_hub import InferenceClient


class HuggingFaceSentimentAnalyzer(SentimentAnalyzer):

    def __init__(self, timeout: int = 10):
        self.model = "nlptown/bert-base-multilingual-uncased-sentiment"
        self.api_key = os.getenv("HUGGINGFACE_API")

    def analyze(self, text: str):
        print(self.api_key)
        print(text)
        client = InferenceClient(
            provider="hf-inference",
            api_key=self.api_key,
        )
        result = client.text_classification(
                text,
                model=self.model,
            )

        return {
            "label": text,
            "score": result
        }
