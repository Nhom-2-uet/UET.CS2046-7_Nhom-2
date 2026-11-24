"""Offline corpus checks and an opt-in live Gemini extraction benchmark."""

from __future__ import annotations

import argparse
import json
import sys
import time
import unittest
from collections import Counter
from datetime import date
from pathlib import Path


AI_PROJECT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = AI_PROJECT_DIR / "APP"
for import_path in (str(APP_DIR), str(AI_PROJECT_DIR)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

CORPUS_PATH = Path(__file__).resolve().parent / "fixtures" / "ai_transaction_cases.jsonl"
EXPECTED_CATEGORIES = {
    "money_shorthand",
    "multiple_transactions",
    "relative_date",
    "ambiguous",
    "missing_information",
}


def load_cases() -> list[dict]:
    with CORPUS_PATH.open(encoding="utf-8") as corpus_file:
        return [json.loads(line) for line in corpus_file if line.strip()]


def canonical_transactions(transactions: list[dict]) -> Counter:
    """Compare the facts users care about, independent of output ordering."""
    return Counter(
        (
            item["amount"],
            item["category"],
            item["type"],
            item.get("date"),
            item.get("date_is_default", False),
        )
        for item in transactions
    )


def field_match_count(expected: list[dict], actual: list[dict], field: str) -> int:
    """Count matching field values without depending on transaction order."""
    expected_values = Counter(item.get(field) for item in expected)
    actual_values = Counter(item.get(field) for item in actual)
    return sum((expected_values & actual_values).values())


class TestAICorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_cases()

    def test_corpus_has_one_hundred_cases(self) -> None:
        self.assertEqual(len(self.cases), 100)

    def test_each_scenario_has_twenty_cases(self) -> None:
        counts = Counter(case["category"] for case in self.cases)
        self.assertEqual(set(counts), EXPECTED_CATEGORIES)
        self.assertEqual(counts, Counter({category: 20 for category in EXPECTED_CATEGORIES}))

    def test_ids_are_unique_and_required_fields_exist(self) -> None:
        ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertTrue(case["input"].strip())
                date.fromisoformat(case["reference_date"])
                self.assertIsInstance(case["expected_transactions"], list)

    def test_expected_transactions_match_extraction_contract(self) -> None:
        allowed_categories = {
            "Ăn uống", "Cà phê", "Đi lại", "Tiền trọ", "Học tập",
            "Giải trí", "Mua sắm", "Sức khỏe", "Khác", "Gia đình gửi",
            "Làm thêm", "Học bổng",
        }
        for case in self.cases:
            for item in case["expected_transactions"]:
                with self.subTest(case_id=case["case_id"], transaction=item):
                    self.assertIsInstance(item["amount"], int)
                    self.assertGreater(item["amount"], 0)
                    self.assertIn(item["category"], allowed_categories)
                    self.assertIn(item["type"], {"income", "expense"})
                    self.assertTrue(item["description"].strip())
                    date.fromisoformat(item["date"])

    def test_missing_information_never_has_expected_transactions(self) -> None:
        cases = [case for case in self.cases if case["category"] == "missing_information"]
        self.assertTrue(cases)
        self.assertTrue(all(case["expected_transactions"] == [] for case in cases))


def run_live_benchmark(limit: int | None = None) -> int:
    from APP.services.ai_service import extract_with_gemini

    cases = load_cases()
    if limit is not None:
        cases = cases[:limit]

    results: dict[str, list[int]] = {
        category: [0, 0] for category in sorted(EXPECTED_CATEGORIES)
    }
    field_totals = Counter()
    field_matches = Counter()
    consecutive_errors = 0

    for index, case in enumerate(cases, start=1):
        category = case["category"]
        results[category][1] += 1
        print(f"[{index}/{len(cases)}] {case['case_id']}: {case['input']}", flush=True)
        try:
            result = extract_with_gemini(
                case["input"],
                reference_date=date.fromisoformat(case["reference_date"]),
            )
            actual = [item.model_dump(mode="json") for item in result.transactions]
            expected = case["expected_transactions"]
            passed = canonical_transactions(actual) == canonical_transactions(expected)
            results[category][0] += int(passed)

            if expected:
                expected_count = len(expected)
                for field in ("amount", "category", "type", "date", "date_is_default"):
                    field_totals[field] += expected_count
                    field_matches[field] += field_match_count(expected, actual, field)

            consecutive_errors = 0
            if not passed:
                print("  FAIL expected:", json.dumps(expected, ensure_ascii=False))
                print("       actual:  ", json.dumps(actual, ensure_ascii=False))
            time.sleep(0.25)
        except Exception as error:
            consecutive_errors += 1
            print(f"  ERROR {type(error).__name__}: {error}")
            if consecutive_errors >= 3:
                print("Stopping after three consecutive API errors.")
                break

    print("\nKết quả theo nhóm:")
    total_passed = total_cases = 0
    for category, (passed, attempted) in results.items():
        print(f"- {category}: {passed}/{attempted}")
        total_passed += passed
        total_cases += attempted
    accuracy = 100 * total_passed / total_cases if total_cases else 0
    print(f"Độ chính xác theo câu: {accuracy:.1f}% ({total_passed}/{total_cases})")
    print("Mục tiêu trong kế hoạch: >= 95%")
    if field_totals:
        print("Độ khớp các trường bắt buộc:")
        for field in ("amount", "category", "type", "date", "date_is_default"):
            correct = field_matches[field]
            total = field_totals[field]
            print(f"- {field}: {100 * correct / total:.1f}% ({correct}/{total})")
    return 0 if total_cases and total_passed == total_cases else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Gemini for the corpus (uses API quota and may incur cost).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Run only the first N corpus cases with --live.",
    )
    arguments = parser.parse_args()
    if arguments.limit is not None and arguments.limit < 1:
        parser.error("--limit must be a positive integer")

    if arguments.live:
        raise SystemExit(run_live_benchmark(arguments.limit))
    unittest.main(argv=[sys.argv[0]], verbosity=2)
