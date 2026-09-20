# preflight_local — law-b39-l5-tasting-programme-checklist-audit

Verdict: **NEEDS_REVIEW**  (NEEDS_REVIEW 1, NOT_APPLICABLE 14, PASS 28)

| criterion | outcome | evidence |
|---|---|---|
| **layer1_clarity_scope** | NEEDS_REVIEW | requirement spans cover 72% of the instruction (J-SPEC tripwire) |
| layer1_clarity_scope__output_surface_contract | PASS | submission_format.md shipped in environment/input/ |
| layer1_clarity_scope__representation_contract | PASS | 3 rendering-tolerant checks (in_array/approx/compound with abs<=1e-3 numeric cells) against 0 exact numeric pins (leading-zero transcription class) |
| layer1_clarity_scope__process_requirement_disclosure | NOT_APPLICABLE | no process requirements in this schema — grading is on delivered files only |
| layer1_clarity_scope__redaction_readability | NOT_APPLICABLE | no redacted fixtures in this schema |
| **layer1_realism_leakage** | PASS | all applicable children pass |
| layer1_realism_leakage__domain_correctness | PASS | BR-/AG- identifiers are bundle-local fiction: no jurisdiction, statute or association is named, and the per-section subject tags are a closed-world construct real law does not carry. The phantom citations (BR-298, BR-299, AG-399) sit deliberately outside the live ranges BR-201-211 and AG-301-311. No external source to reconcile against — correctness is fully determined by the shipped fixtures, and grading never leaves the container. |
| layer1_realism_leakage__authoritative_reference_validity | NOT_APPLICABLE | no citations in the instruction |
| layer1_realism_leakage__workflow_realism | PASS | Recognisable ask: trade-guidance drifting from the regulation is a standard beverage-compliance failure mode, and the central conflict — non-employee staff believing the brand's permit covers them, 'the practice for years' — mirrors how real solicitor-permit rules are misread. The deliverable shape (per-item verdict carrying the governing authority) is what a compliance review produces. Scope is narrower than real practice: the three UNADDRESSED items would be escalated as open risk rather than closed, and IT-113's ordinance would actually be checked — accepted as closed-world simplification, not a realism defect. |
| layer1_realism_leakage__golden_isolation | PASS | Dockerfile copies input/ only; tests and solution never enter the task image |
| **layer1_package_consistency** | PASS | all applicable children pass |
| layer1_package_consistency__manifest_environment_consistency | NOT_APPLICABLE | no manifest in the harbor-cli layout (P2) |
| layer1_package_consistency__declared_executed_verifier_consistency | PASS | all 10 declared checks executed by the real engine against the shipped gold |
| layer1_package_consistency__cross_artifact_consistency | PASS | requirement table names only shipped checks; census consistent with tests/verifier.json |
| layer1_package_consistency__instruction_verifier_consistency | PASS | every deliverable carries content checks, every surface is paired, and the hollow/incomplete lanes prove the requirement->check direction executably |
| layer1_package_consistency__solution_instruction_consistency | PASS | gold conforms to the contract and the page (gold_conformance) |
| layer1_package_consistency__solution_verifier_consistency | PASS | gold scores 1.0 and every hollow/incomplete variant of it fails — accepted for the right reasons |
| layer1_package_consistency__artifact_contract_consistency | PASS | every graded surface is a contracted deliverable |
| **layer5_verifier_fairness_static** | PASS | all applicable children pass |
| layer5_verifier_fairness_static__score_bucket_activation | NOT_APPLICABLE | no score buckets — file_check core gate + weights |
| layer5_verifier_fairness_static__aggregation_normalization | PASS | two-tier scoring: 8 core / 2 incidental; partial-pass verified: one failed incidental costs 0.100, reward 0.900; any core failure zeroes |
| layer5_verifier_fairness_static__evidence_routing | PASS | all checks read workspace-relative deliverables |
| layer5_verifier_fairness_static__verifier_execution_completeness | PASS | every check executes and passes on gold (real engine) |
| layer5_verifier_fairness_static__semantic_equivalence | PASS | 8 cosmetic renderings and 4 value-correct rewordings of the answer all still score 1.0 (recorded reward 1.0 on every rewording) |
| layer5_verifier_fairness_static__surface_form_brittleness | PASS | 8 cosmetic renderings and 4 value-correct rewordings of the answer all still score 1.0 (recorded reward 1.0 on every rewording) |
| layer5_verifier_fairness_static__coverage_depth | PASS | every deliverable carries content checks, every surface is paired, and the hollow/incomplete lanes prove the requirement->check direction executably |
| layer5_verifier_fairness_static__scoring_proportionality | PASS | every declared deliverable scores 0 when ABSENT and 0 when HOLLOW (mutations.json: 3 incomplete + 2 hollow replays, all reward 0); weight share by deliverable: answer.md 40%, checklist_audit.csv 40%, results.json 20% |
| layer5_verifier_fairness_static__check_independence | PASS | 1 figure(s) paid more than once, all disclosed in requirements.json with a single CORE payer (results.json); the artifact copies are incidental and cannot zero the task: 7 (results_figures+answer_wrong_figure) |
| layer5_verifier_fairness_static__counterfactual_strength | PASS | positive + negative + incomplete + adversarial cases ship (test_outputs.py lanes) with mutation evidence in consistency/mutations.json |
| layer5_verifier_fairness_static__requirement_traceability | PASS | check->requirement direction closed (no orphan checks) |
| layer5_verifier_fairness_static__process_grading_justification | NOT_APPLICABLE | no process grading — files only |
| **layer5_reward_hacking_static** | PASS | all applicable children pass |
| layer5_reward_hacking_static__rollout_legitimacy | PASS | grading is deterministic file inspection only — no network, no state, no judge |
| layer5_reward_hacking_static__sanctioned_interface_use | PASS | every graded surface is a contracted deliverable |
| layer5_reward_hacking_static__state_spoofing | NOT_APPLICABLE | no gym/connector state to spoof — static file grading |
| layer5_reward_hacking_static__golden_or_internal_access | PASS | Dockerfile copies input/ only; tests and solution never enter the task image |
| **layer5_llm_judge_design** | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__judge_context_completeness | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__judge_context_truncation | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__judge_failure_handling | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__artifact_grounding | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__judge_execution_validity | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__repeat_stability | NOT_APPLICABLE | no LLM judge in the verifier |
