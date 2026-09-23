-- Evaluation-only fixture. Apply only to a disposable database ending in _test.
TRUNCATE monitoring_runs CASCADE;

INSERT INTO monitoring_runs (id, trigger_type, product, offering_id, query, status, queued_at, started_at, completed_at, summary) VALUES
('10000000-0000-0000-0000-000000000001','api','consumer_loan','consumer_standard','eval previous','succeeded',now()-interval '90 days',now()-interval '90 days',now()-interval '90 days','{}'),
('10000000-0000-0000-0000-000000000002','api','consumer_loan','consumer_standard','eval stale','succeeded',now()-interval '10 days',now()-interval '10 days',now()-interval '10 days','{}'),
('10000000-0000-0000-0000-000000000003','api','consumer_loan','consumer_standard','eval pending','awaiting_review',now()-interval '1 day',now()-interval '1 day',NULL,'{}'),
('10000000-0000-0000-0000-000000000004','api','mortgage','mortgage_express','eval fresh','succeeded',now()-interval '1 day',now()-interval '1 day',now()-interval '1 day','{}');

INSERT INTO offering_executions (id, run_id, product, offering_id, status, current_stage, started_at, completed_at, review_count) VALUES
('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','consumer_loan','consumer_standard','succeeded','published',now()-interval '90 days',now()-interval '90 days',0),
('20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','consumer_loan','consumer_standard','succeeded','published',now()-interval '10 days',now()-interval '10 days',0),
('20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000003','consumer_loan','consumer_standard','candidate_review','published',now()-interval '1 day',now()-interval '1 day',1),
('20000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000004','mortgage','mortgage_express','succeeded','published',now()-interval '1 day',now()-interval '1 day',0);

INSERT INTO tariff_snapshots (id,run_id,offering_execution_id,bank,product,offering_id,status,normalized_tariff,evidence,semantic_extraction,validation,canonical_sha256,previous_accepted_snapshot_id,created_at,accepted_at) VALUES
('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','ameria','consumer_loan','consumer_standard','accepted','{"nominal_interest_rate":"12.0%"}','[{"source_url":"https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans","excerpt":"Nominal interest rate: 12.0%"}]','{}','{"decision":"accept"}',repeat('a',64),NULL,now()-interval '90 days',now()-interval '90 days'),
('30000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','ameria','consumer_loan','consumer_standard','accepted','{"nominal_interest_rate":"13.5%"}','[{"source_url":"https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans","excerpt":"Nominal interest rate: 13.5%"}]','{}','{"decision":"accept"}',repeat('b',64),'30000000-0000-0000-0000-000000000001',now()-interval '10 days',now()-interval '10 days'),
('30000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000003','ameria','consumer_loan','consumer_standard','review_required','{"nominal_interest_rate":"99.0%"}','[{"source_url":"https://ameriabank.am/review-only","excerpt":"Candidate only: 99.0%"}]','{}','{"decision":"review"}',repeat('c',64),'30000000-0000-0000-0000-000000000002',now()-interval '1 day',NULL),
('30000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000004','ameria','mortgage','mortgage_express','accepted','{"nominal_interest_rate":"9.75%"}','[{"source_url":"https://ameriabank.am/en/personal/loans/mortgage/express-loan","excerpt":"Nominal interest rate: 9.75%"}]','{}','{"decision":"accept"}',repeat('d',64),NULL,now()-interval '1 day',now()-interval '1 day');

INSERT INTO tariff_changes (id,run_id,product,offering_id,previous_snapshot_id,current_snapshot_id,changes,change_count,created_at) VALUES
('40000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000002','consumer_loan','consumer_standard','30000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000002','[{"field":"nominal_interest_rate","previous":"12.0%","current":"13.5%"}]',1,now()-interval '10 days');
