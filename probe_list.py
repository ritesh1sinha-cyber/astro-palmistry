import sys, json
sys.path.insert(0, 'engines')
from astro.llm.facts import ReportFacts, public_fact_payload
from astro.llm.rules import _compact_report_payload
import os
for f in os.listdir('ci-storage'):
    print(f)
