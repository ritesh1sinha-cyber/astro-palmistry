import re
html = open('sample_full_report.html', encoding='utf-8').read()
start = html.find('</style>')
content = html[start:]
cards = re.findall(r'<article class="card conv-area".*?</article>', content, re.S)
print(f'Total area cards: {len(cards)}')
for i, c in enumerate(cards):
    area = re.search(r'class="area">(.*?)</span>', c, re.S)
    concl = re.search(r'consultation-conclusion.*?<p>(.*?)</p>', c, re.S)
    remedy = re.search(r'consultation-remedy.*?<p>(.*?)</p>', c, re.S)
    print(f'\n--- AREA {i+1}: {area.group(1) if area else "?"} ---')
    print('CONCLUSION:', (concl.group(1) if concl else 'NONE')[:600])
    print('REMEDY:', (remedy.group(1) if remedy else 'NONE')[:250])