from abc import ABC, abstractmethod

class SentimentAnalyzer(ABC):

    @abstractmethod
    def analyze(self, text: str) -> dict:
        pass
