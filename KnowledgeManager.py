from langchain_experimental.text_splitter import SemanticChunker
import whisper
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from typing import Iterable
from ConfigurationManager import ConfigurationManager
from qdrant_client.http.models import VectorParams, Distance

class KnowledgeManager:
    def __init__(self):
        config = ConfigurationManager.get_configuration("knowledgeManager")
        embeddings = HuggingFaceEmbeddings(model="Qwen/Qwen3-Embedding-0.6B")

        if config["database"] == "chroma":
            self.vectorStore = Chroma(
                collection_name="capstone",
                embedding_function=embeddings,
                persist_directory="./chroma_langchain_db",
            )
        elif config["database"] == "qdrant":
            qdrant = QdrantClient(url="http://localhost:6333")
            if not qdrant.collection_exists("capstone"):
                qdrant.create_collection(
                    collection_name="capstone",
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE))
            self.vectorStore = QdrantVectorStore.from_existing_collection(
                embedding=embeddings,
                collection_name="capstone",
                url="http://localhost:6333"
            )
        else:
            raise ValueError('Unknown database type')

        if config["splitterType"] == "recursive":
            self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
        elif config["splitterType"] == "semantic":
            self.text_splitter = SemanticChunker(embeddings=embeddings, breakpoint_threshold_amount=75)
        else:
            raise ValueError("Unknown splitter type")

    def import_audio(self, audio_file_path: str):
        print(f"Importing audio from {audio_file_path}")
        whisper_model = whisper.load_model("small")
        result = whisper_model.transcribe(audio=audio_file_path)
        print("Transcription complete.")
        document = Document(result["text"], metadata={"source": "audio-transcript", "path": audio_file_path})
        self.import_documents([document])

    def import_pdf(self , pdf_file_path: str):
        print(f"Importing pdf from {pdf_file_path}")
        loader = PyMuPDFLoader(pdf_file_path)
        documents = loader.load()

        self.import_documents(documents)

    def import_documents(self, documents: Iterable[Document]):
        splits = self.text_splitter.split_documents(documents)
        self.vectorStore.add_documents(splits)
        print("Import complete.")

    def get_retriever(self):
        return self.vectorStore.as_retriever()

