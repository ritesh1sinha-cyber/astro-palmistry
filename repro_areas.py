import datetime
from core.llm_client import complete_model
from engines.astro.llm.schemas import ConversationalAreasProse, CardFacts, ReportFacts
from engines.astro.llm.rules import system_prompt_for, user_prompt

cards = [
    CardFacts(area='career', label='Work & Career', status='mixed', activation_status='weak', confidence='moderate', prediction_strength='moderate'),
    CardFacts(area='love', label='Relationships & Partnership', status='promise', activation_status='inactive', confidence='moderate', prediction_strength='moderate'),
    CardFacts(area='money', label='Money', status='weak', activation_status='inactive', confidence='low', prediction_strength='weak'),
    CardFacts(area='children', label='Children', status='promise', activation_status='active', confidence='high', prediction_strength='strong'),
]
facts = ReportFacts(access='paid', cards=cards, first_name='Test')

print('calling complete_model for areas...')
res = complete_model(
    ConversationalAreasProse,
    system_prompt_for('full_report_areas'),
    user_prompt(facts, schema_name='ConversationalAreasProse', section='areas'),
)
print('RESULT:', 'None' if res is None else type(res).__name__)
if res is not None:
    print('areas:', [(a.area, len(a.conclusion)) for a in res.areas])
