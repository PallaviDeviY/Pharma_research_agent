# Retrieval evaluation set

`data/processed/gold_queries.jsonl` contains 40 query-to-source judgments, split evenly across four controlled-scope drugs. Each query points to a source record identifier, not to a generated answer. The judgments anchor well-known registered outcome trials and their PubMed primary publications:

- Semaglutide: ClinicalTrials.gov NCT01720446 and PubMed PMID 27633186.
- Empagliflozin: ClinicalTrials.gov NCT01131676 and PubMed PMID 26378978.
- Dapagliflozin: ClinicalTrials.gov NCT03036124 and PubMed PMID 31535829.
- Liraglutide: ClinicalTrials.gov NCT01179048 and PubMed PMID 27295427.

The IDs can be inspected at their official records: [ClinicalTrials.gov NCT01720446](https://clinicaltrials.gov/study/NCT01720446), [NCT01131676](https://clinicaltrials.gov/study/NCT01131676), [NCT03036124](https://clinicaltrials.gov/study/NCT03036124), [NCT01179048](https://clinicaltrials.gov/study/NCT01179048), and [PubMed 27633186](https://pubmed.ncbi.nlm.nih.gov/27633186/), [26378978](https://pubmed.ncbi.nlm.nih.gov/26378978/), [31535829](https://pubmed.ncbi.nlm.nih.gov/31535829/), [27295427](https://pubmed.ncbi.nlm.nih.gov/27295427/).

The query paraphrases are an initial manually curated set, not a statistically representative benchmark. A research team should expand it with multiple independently judged relevant documents per query and record a second reviewer’s adjudication before using the scores for release decisions. Run the current retrieval comparison after ingestion with `python -m pharma_intelligence.evaluation.run_retrieval`.
