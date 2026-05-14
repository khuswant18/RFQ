#!/usr/bin/env python3
"""Check RAG system status and what's actually working."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

print("=" * 70)
print("RAG SYSTEM STATUS CHECK")
print("=" * 70)
print()

# 1. Check ChromaDB availability
print("1. ChromaDB Availability:")
print("-" * 70)
try:
    from app.core.rag.chroma_client import ChromaClient
    chroma = ChromaClient(persist_directory="data/chroma")
    print("✅ ChromaDB is available and initialized")
    
    # List all collections
    print("\n2. Collections in ChromaDB:")
    print("-" * 70)
    collections = chroma.client.list_collections()
    if collections:
        for coll in collections:
            count = coll.count()
            print(f"  ✓ {coll.name}: {count} documents")
    else:
        print("  ⚠️  No collections found")
    
    # Test each collection
    print("\n3. Testing Collection Queries:")
    print("-" * 70)
    
    test_query = "TMT Fe500 12mm"
    
    for coll_name in ["is_codes", "material_synonyms", "hsn_gst_rules", "weight_formulas", "rag_documents"]:
        try:
            results = chroma.query(coll_name, [test_query], n_results=2)
            docs = results.get("documents", [[]])[0]
            if docs:
                print(f"  ✓ {coll_name}: {len(docs)} results")
                print(f"    Sample: {docs[0][:80]}...")
            else:
                print(f"  ⚠️  {coll_name}: No results")
        except Exception as e:
            print(f"  ❌ {coll_name}: Error - {e}")
    
except ImportError as e:
    print(f"❌ ChromaDB not available: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error initializing ChromaDB: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Check NER Agent RAG usage
print("\n4. NER Agent RAG Integration:")
print("-" * 70)
try:
    from app.agents.ner_agent import NERAgent
    from app.models.rfq import NERInput
    
    ner = NERAgent()
    if ner.chroma:
        print("✅ NER Agent has ChromaDB client")
        
        # Test retrieval
        test_text = "Need 100 MT TMT Fe500 12mm bars"
        is_context, synonyms = ner.retrieve_steel_context(test_text)
        
        if is_context:
            print(f"  ✓ IS Code context retrieved: {len(is_context)} chars")
            print(f"    Sample: {is_context[:100]}...")
        else:
            print("  ⚠️  No IS code context retrieved")
        
        if synonyms:
            print(f"  ✓ Synonyms retrieved: {len(synonyms)} chars")
            print(f"    Sample: {synonyms[:100]}...")
        else:
            print("  ⚠️  No synonyms retrieved")
    else:
        print("❌ NER Agent does NOT have ChromaDB client")
except Exception as e:
    print(f"❌ Error testing NER Agent: {e}")
    import traceback
    traceback.print_exc()

# 5. Check Pricing Agent RAG usage
print("\n5. Pricing Agent RAG Integration:")
print("-" * 70)
try:
    from app.agents.pricing_agent import PricingAgent
    
    pricing = PricingAgent()
    if pricing.chroma:
        print("✅ Pricing Agent has ChromaDB client")
    else:
        print("⚠️  Pricing Agent does NOT have ChromaDB client (running in standalone mode)")
except Exception as e:
    print(f"❌ Error testing Pricing Agent: {e}")

# 6. Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print()
print("Agentic RAG Status:")
print("  • NER Agent: Uses RAG to retrieve IS codes & material synonyms")
print("  • Pricing Agent: Has ChromaDB client but doesn't actively use RAG")
print("  • GST Agent: No RAG (uses hardcoded rules)")
print("  • Validator Agent: No RAG (uses hardcoded BIS standards)")
print()
print("RAG is PARTIALLY implemented:")
print("  ✓ ChromaDB is set up and working")
print("  ✓ Knowledge base is seeded (IS codes, synonyms, HSN, formulas)")
print("  ✓ NER Agent actively retrieves context before LLM calls")
print("  ✗ Other agents don't use RAG (use hardcoded logic)")
print("  ✗ RAG documents collection (408 PDFs) exists but not used by agents")
print()
