"""Evaluate the RAG pipeline against a golden dataset."""
import json
import time
from dotenv import load_dotenv

from generator import answer

load_dotenv()


def evaluate():
    # Load dataset
    with open("eval_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Running evaluation on {len(dataset)} questions...\n")

    retrieval_hits = 0
    answer_hits = 0
    total_latency = 0.0

    for item in dataset:
        q_id = item["id"]
        query = item["question"]
        expected_facts = [f.lower() for f in item["expected_facts"]]
        expected_chunks = set(item["expected_chunks"])

        print(f"Q{q_id}: {query}")

        # Run the RAG pipeline and measure time
        start_time = time.time()
        try:
            result = answer(query, top_k=3)
        except Exception as e:
            print(f"  [ERROR] Pipeline failed: {e}\n")
            continue
        latency = time.time() - start_time
        total_latency += latency

        # 1. Evaluate Retrieval
        retrieved_chunks = set(result["sources"])
        retrieval_hit = bool(expected_chunks.intersection(retrieved_chunks))
        if retrieval_hit:
            retrieval_hits += 1
            print(f"  [PASS] Retrieval: Found {retrieved_chunks.intersection(expected_chunks)}")
        else:
            print(f"  [FAIL] Retrieval: Expected {expected_chunks}, got {retrieved_chunks}")

        # 2. Evaluate Generation
        answer_text = result["answer"].lower()
        
        # Check if all expected facts are in the answer
        import re
        def normalize(text):
            # lowercase, remove punctuation, collapse spaces
            text = text.lower()
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

        normalized_answer = normalize(answer_text)
         # Check if expected facts are present (allowing for word order changes)
        missing_facts = []
        for fact in expected_facts:
            norm_fact = normalize(fact)
            # Check if the fact string exists, or if the individual words exist nearby
            if norm_fact not in normalized_answer:
                # Fallback: check if all significant words from the fact are in the answer
                words = [w for w in norm_fact.split() if len(w) > 2]
                if not all(w in normalized_answer for w in words):
                    missing_facts.append(fact)
        
        if not missing_facts:
            answer_hits += 1
            print(f"  [PASS] Answer: Contains all expected facts. ({latency:.2f}s)")
        else:
            print(f"  [FAIL] Answer: Missing facts: {missing_facts} ({latency:.2f}s)")

        print()

    # Final Scorecard
    total = len(dataset)
    retrieval_accuracy = (retrieval_hits / total) * 100
    answer_accuracy = (answer_hits / total) * 100
    avg_latency = total_latency / total

    print("=" * 40)
    print("EVALUATION SCORECARD")
    print("=" * 40)
    print(f"Total Questions: {total}")
    print(f"Retrieval Accuracy (Hit Rate): {retrieval_accuracy:.1f}% ({retrieval_hits}/{total})")
    print(f"Answer Accuracy (Fact Match): {answer_accuracy:.1f}% ({answer_hits}/{total})")
    print(f"Average Latency: {avg_latency:.2f}s")
    print("=" * 40)

    return retrieval_accuracy, answer_accuracy


if __name__ == "__main__":
    evaluate()