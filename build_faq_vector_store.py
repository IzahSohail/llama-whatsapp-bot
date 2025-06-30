import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import os
from chromadb.config import Settings

class FAQVectorStore:
    def __init__(self, faq_document_paths: List[str], persist_directory: str = "faq_vector_store"):
        """
        Initialize the FAQ vector store.
        
        Args:
            faq_document_paths: A list of paths to text files containing FAQ content.
            persist_directory: Directory to persist the vector store.
        """
        self.faq_document_paths = faq_document_paths
        self.persist_directory = persist_directory
        
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_or_create_collection(
            name="faqs",
            embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        )
        
    def _load_all_document_text(self) -> str:
        """
        Loads and combines text from all specified document paths.
        Assumes .txt files for now.
        """
        combined_text = []
        for path in self.faq_document_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    combined_text.append(f.read())
            except FileNotFoundError:
                raise
            except Exception as e:
                raise
        return "\n\n".join(combined_text) # Use double newline as separator between documents

    def _chunk_text(self, text: str) -> List[str]:
        """
        Simple text chunking by paragraphs.
        This can be enhanced later for more sophisticated chunking.
        """
        # Split by double newlines to get paragraphs
        chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
        return chunks

    def build_vector_store(self):
        """
        Build the vector store from the raw FAQ text.
        Only builds if the collection is empty.
        """
        if self.collection.count() > 0:
            return
        
        raw_faq_text = self._load_all_document_text()
        chunks = self._chunk_text(raw_faq_text)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({"source": "Combined FAQ Documents", "chunk_id": i})
            ids.append(f"faq_chunk_{i}")
        
        if documents: # Only add if there are documents
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        else:
            pass

    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant FAQ chunks similar to the query.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        formatted_results = []
        if results and results["ids"]: # Check if results and ids exist and are not empty
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })
        return formatted_results

if __name__ == "__main__":
    # List of paths to your FAQ text files
    faq_document_paths = [
        "Siraa_overview.txt",
        "real_estate_101_content.txt"
    ]
    
    faq_store = FAQVectorStore(faq_document_paths=faq_document_paths)
    faq_store.build_vector_store()
    
    query = "What is Siraa's value proposition?"
    search_results = faq_store.search(query)
    
    query = "How does remote property investment work?"
    search_results = faq_store.search(query) 