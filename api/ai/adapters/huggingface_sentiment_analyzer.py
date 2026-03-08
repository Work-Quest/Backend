from api.ai.ports.sentiment_analyzer import SentimentAnalyzer
import os
from huggingface_hub import InferenceClient


class HuggingFaceSentimentAnalyzer(SentimentAnalyzer):

    def __init__(self, timeout: int = 10):
        self.model = "nlptown/bert-base-multilingual-uncased-sentiment"
        self.api_key = os.getenv("HUGGINGFACE_API")

    def convert_result(self, result):
        print(result)
        max_lable = ""
        max_score = 0
        for i in result:
            if i.score > max_score:
                max_score = i.score
                max_lable = i.label
        return int(max_lable[0])

    def analyze(self, text: str):
        client = InferenceClient(
            provider="hf-inference",
            api_key=self.api_key,
        )
        result = client.text_classification(
                text,
                model=self.model,
            )
    
        score = self.convert_result(result)
    

        return {
            "label": text,
            "score": score
        }
