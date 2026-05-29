import re

with open('app/Home.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all '""", unsafe_allow_html=True)' with '""")' 
# but only within the st.html() blocks (lines 120+)
old = '""", unsafe_allow_html=True)'
new = '""")'
count = content.count(old)
print(f'Found {count} occurrences to replace')
content = content.replace(old, new)

with open('app/Home.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done - replaced all occurrences')
