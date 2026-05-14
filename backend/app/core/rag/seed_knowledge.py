"""Seed steel domain knowledge into ChromaDB."""
import json
import os
import pathlib


class KnowledgeSeeder:
    """Seeds ChromaDB with steel domain knowledge."""

    def __init__(self):
        # Resolve knowledge directory relative to this file
        self.base_dir = pathlib.Path(__file__).resolve().parent.parent.parent
        self.knowledge_dir = self.base_dir / "knowledge"

    def load_json(self, file_path: str):
        """Load JSON data from a file."""
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {file_path} not found.")
            return []

    def seed_is_codes(self, chroma=None):
        """Seed IS codes into ChromaDB."""
        print("Seeding IS codes...")
        data = self.load_json(self.knowledge_dir / "is_codes.json")
        if not data:
            return

        docs = []
        ids = []
        metadatas = []

        for item in data.get("is_codes", []):
            doc = f"{item['is_code']}: {item['title']}. Grades: {', '.join(item['grades'])}. {item['description']}"
            docs.append(doc)
            ids.append(item["id"])
            metadatas.append({"is_code": item["is_code"], "grades": ", ".join(item["grades"])})

        if chroma:
            chroma.add_documents("is_codes", docs, ids, metadatas)
        print(f"  Seeded {len(docs)} IS codes")

    def seed_material_synonyms(self, chroma=None):
        """Seed material synonyms into ChromaDB."""
        print("Seeding material synonyms...")
        data = self.load_json(self.knowledge_dir / "material_synonyms.json")
        if not data:
            return

        docs = []
        ids = []
        metadatas = []

        for item in data:
            doc = f"{item['alias']} means {item['canonical']}: {item['context']}"
            docs.append(doc)
            ids.append(item["id"])
            metadatas.append({"alias": item["alias"], "canonical": item["canonical"]})

        if chroma:
            chroma.add_documents("material_synonyms", docs, ids, metadatas)
        print(f"  Seeded {len(docs)} material synonyms")

    def seed_hsn_gst_rules(self, chroma=None):
        """Seed HSN/GST rules into ChromaDB."""
        print("Seeding HSN/GST rules...")
        data = self.load_json(self.knowledge_dir / "hsn_gst_rules.json")
        if not data:
            return

        docs = []
        ids = []
        metadatas = []

        for item in data:
            doc = f"Material: {item['material']}, HSN Code: {item['hsn_code']}, GST Rate: {item['gst_rate']}. {item['description']}"
            docs.append(doc)
            ids.append(item["id"])
            metadatas.append({"material": item["material"], "hsn_code": item["hsn_code"]})

        if chroma:
            chroma.add_documents("hsn_gst_rules", docs, ids, metadatas)
        print(f"  Seeded {len(docs)} HSN/GST rules")

    def seed_weight_formulas(self, chroma=None):
        """Seed weight formulas into ChromaDB."""
        print("Seeding weight formulas...")
        data = self.load_json(self.knowledge_dir / "weight_formulas.json")
        if not data:
            return

        docs = []
        ids = []
        metadatas = []

        for item in data:
            doc = f"Material: {item['material']}, Formula: {item['formula']}. {item['description']}. Example: {item['example']}"
            docs.append(doc)
            ids.append(item["id"])
            metadatas.append({"material": item["material"], "formula": item["formula"]})

        if chroma:
            chroma.add_documents("weight_formulas", docs, ids, metadatas)
        print(f"  Seeded {len(docs)} weight formulas")

    def seed_external_rag_files(self, chroma=None):
        """Seed external RAG files into ChromaDB."""
        rag_dir = os.getenv("RAG_FILES_PATH", "RAGFiles")
        rag_path = pathlib.Path(rag_dir)
        
        # If relative path, resolve from project root
        if not rag_path.is_absolute():
            project_root = self.base_dir.parent.parent  # Go up from backend/app/core to project root
            rag_path = project_root / rag_dir
        
        if not rag_path.exists():
            raise RuntimeError(f"RAG files directory not found: {rag_path}")

        docs = []
        ids = []
        metadatas = []

        for file_path in rag_path.glob("**/*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in (".txt", ".md"):
                continue

            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                continue

            chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
            for idx, chunk in enumerate(chunks):
                docs.append(chunk)
                ids.append(f"{file_path.stem}_{idx}")
                metadatas.append({"source": str(file_path), "chunk": idx})

        if chroma:
            chroma.add_documents("external_rag_files", docs, ids, metadatas)
        print(f"  Seeded {len(docs)} external RAG chunks")

    def seed_all(self):
        """Seed all knowledge."""
        print("\n🌱 Seeding ChromaDB with steel domain knowledge...")

        from app.core.rag.chroma_client import ChromaClient
        chroma = ChromaClient()

        self.seed_is_codes(chroma)
        self.seed_material_synonyms(chroma)
        self.seed_hsn_gst_rules(chroma)
        self.seed_weight_formulas(chroma)
        self.seed_external_rag_files(chroma)
        print("✅ Knowledge seeding complete!\n")


def seed_chroma():
    """Main entry point for knowledge seeding."""
    seeder = KnowledgeSeeder()
    seeder.seed_all()
