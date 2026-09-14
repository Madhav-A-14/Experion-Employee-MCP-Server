"""
Custom DeepEval metric that computes cosine similarity between 
expected_output and actual_output using sentence embeddings.
Connects into the same evaluate() pipeline as MCPUseMetric.

Uses Voyage AI's voyage-4-nano model, loaded locally via sentence-transformers.
"""

import numpy as np
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL_NAME


_model = None


def _get_model():
    
    global _model
    if _model is None:
        _model = SentenceTransformer(
            EMBEDDING_MODEL_NAME,
            trust_remote_code=True,
            
        )
    return _model
    

class CosineSimilarityMetric(BaseMetric):
    
    def __init__(self,threshold:float = 0.75):
        
        super().__init__() # Runs BaseMetric's own class first so that it is properly initialised.
        self.threshold = threshold
        self.score = 0.0
        self.success = False
        self.reason = ""
        
        
    def _get_embeddings(self, text:str) -> np.ndarray:
        """
        Sends one piece of text through the local voyage-4-nano model and
        gets back its embedding — a list of numbers representing the
        text's "meaning" as a vector.
            
        """
        model = _get_model() 
        return model.encode(text, convert_to_numpy = True) 
        
    
        
    def measure(self,test_case : LLMTestCase, *args, **kwargs) -> float:
            
        """
        This is the main method DeepEval calls for every test case.
        It compares the expected output vs the actual output and scores
        how similar they are, from 0 (totally different) to 1 (identical meaning).
        """
            
        # Extracting expected_output and Actual_output from test_case
        expected = test_case.expected_output or ""
        actual = test_case.actual_output or ""
            
        # Turning both into embedding vectors.
        expected_vectorized = self._get_embeddings(expected)
        actual_vectorized = self._get_embeddings(actual)
            
        # Cosine Similarity Formula -- 1.0 -> Very similar meaning , 0 -> Opposite meaning
                        
        #                A · B
        #  cos(θ)  =  ─────────────
         #              ||A|| × ||B||
            
           
        similarity = np.dot(expected_vectorized, actual_vectorized) / (
            np.linalg.norm(expected_vectorized) * np.linalg.norm(actual_vectorized)
        )
            
        self.score = float(similarity) 
        self.success = self.score>= self.threshold 
        self.reason = f"Cosine Similarity between Actual Output and Expected Output : {self.score:.3f}"
        
        return self.score
    
    async def a_measure(self, test_case:LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)
    
    
    def is_successful(self) ->bool:
        return self.success
    
    @property
    def __name__(self):
        # The label DeepEval will show for this metric in the results/report.
        
        return "Output Similarity"
      
        
        