"""Offline dev metric denominator, final-model context and real-cost accounting contracts."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.dev_evaluation import evaluate_case, summarize, usage_totals


class DevEvaluationTests(unittest.TestCase):
    def test_unanswerable_never_in_retrieval_denominator(self):
        chunk=dict(id="c",text="Full evidence.",source_id="doc",source="doc.pdf",page=1,metadata={})
        yes=dict(id="a",answerable=True,gold=[dict(source_id="doc",page=1,evidence="Full evidence.")])
        no=dict(id="b",answerable=False,gold=[])
        agent=dict(status="answered",model_context="Full evidence.",model_context_ids=["c"],
                   citations=["c"],search_count=1,model_call_count=2,model_calls=[],elapsed_seconds=1)
        records=[]
        for case in [yes,no]:
            records.append(dict(profile="p",agent=agent,raw=dict(elapsed_ms=1),
                                embedding_requests=[],evaluation=evaluate_case(case,[chunk],agent,{"c":chunk})))
        result=summarize(records,"p")
        self.assertEqual(result["cases"],2)
        self.assertEqual(result["original_query_evidence_hit_at_3_literal"],dict(n=1,N=1,rate=1))
        self.assertIsNone(records[1]["evaluation"]["raw_hit_at_1_literal"])

    def test_context_must_be_sent_not_only_planned_and_errors_miss(self):
        chunk=dict(id="c",text="gold",source_id="doc",page=1)
        case=dict(id="q",answerable=True,gold=[dict(source_id="doc",page=1,evidence="gold")])
        agent=dict(status="error",context="gold",model_context="gold",model_context_ids=["c"])
        self.assertFalse(evaluate_case(case,[],agent,{"c":chunk})["final_model_context_evidence_literal"])
        agent.update(status="answered",model_context="")
        self.assertFalse(evaluate_case(case,[chunk],agent,{"c":chunk})["final_model_context_evidence_literal"])

    def test_unknown_cost_is_not_zero(self):
        result=usage_totals([{"usage":{"cost":0.02,"prompt_tokens":5}}, {"usage":None}])
        self.assertEqual(result["known_cost_usd"],0.02)
        self.assertIsNone(result["cost_usd"])
        self.assertEqual(result["unknown_cost_request_count"],1)
        self.assertEqual(usage_totals([])["cost_usd"],0)


if __name__=="__main__":unittest.main()
