"""Seed steel domain knowledge into ChromaDB."""
import json
import os


class KnowledgeSeeder:
    """Seeds ChromaDB with steel domain knowledge."""

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
        data = self.load_json("app/knowledge/is_codes.json")
        if not data:
            return

        docs = []
        ids = []
        metadatas = []

        for item in data.get("is_codes", []):
            doc = f"{item['is_code']}: {item['title']}. Grades: {', '.join(item['grades'])}. {item['description']}"
            docs.append(doc)
            ids.append(item["id"])
            metadatas.append({"is_code": item["is_code"], "grades": item["grades"]})

        if chroma:
            chroma.add_documents("is_codes", docs, ids, metadatas)
        print(f"  Seeded {len(docs)} IS codes")

    def seed_material_synonyms(self, chroma=None):
        """Seed material synonyms into ChromaDB."""
        print("Seeding material synonyms...")
        data = self.load_json("app/knowledge/material_synonyms.json")
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
        data = self.load_json("app/knowledge/hsn_gst_rules.json")
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
        data = self.load_json("app/knowledge/weight_formulas.json")
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

    def seed_all(self):
        """Seed all knowledge."""
        print("\n🌱 Seeding ChromaDB with steel domain knowledge...")

        try:
            from app.core.rag.chroma_client import ChromaClient
            chroma = ChromaClient()
        except ImportError:
            print("Warning: ChromaDB not available. Skipping seeding.")
            chroma = None

        self.seed_is_codes(chroma)
        self.seed_material_synonyms(chroma)
        self.seed_hsn_gst_rules(chroma)
        self.seed_weight_formulas(chroma)
        print("✅ Knowledge seeding complete!\n")


def seed_chroma():
    """Main entry point for knowledge seeding."""
    seeder = KnowledgeSeeder()
    seeder.seed_all()
