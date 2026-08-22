import os

def fix_file(filepath, replacements):
    if not os.path.exists(filepath): return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('frontend/web-app/src/components/DetailViews/AILearningDetail.tsx', [
    ('{recentSessions.map((session: any, idx: number) => (', '{recentSessions.map((session: unknown, idx: number) => (')
])

fix_file('frontend/web-app/src/components/DetailViews/SettingsDetail.tsx', [
    ('{availableVoices.map((voice: any) => (', '{availableVoices.map((voice: unknown) => (')
])

fix_file('frontend/web-app/src/contexts/DashboardContext.tsx', [
    ('catch(e)', 'catch(_e)')
])
