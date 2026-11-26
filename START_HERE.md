# START HERE — Kaise chalana hai

## Zaroori cheezein (pehle install kar lein)
- Claude Code (`npm install -g @anthropic-ai/claude-code`)
- Python 3.10+
- Node.js 18+
- Docker Desktop (Docker Compose ke saath)
- Git

## Steps
1. Zip extract karein. Folder ka naam: `oman-faq-chatbot`
2. Terminal kholein aur folder mein jayein:
   ```
   cd oman-faq-chatbot
   claude
   ```
3. `Shift+Tab` dabakar **Plan Mode** on karein.
4. `BUILD_PROMPT.md` ka poora content copy karke Claude Code mein paste karein
   (ya simply likhein: `Read BUILD_PROMPT.md and execute it phase by phase`).
5. Plan dekh kar approve karein. Claude Code phase-by-phase sab bana dega.

## Agar beech mein context full ho jaye
```
/clear
Read CLAUDE.md and PROGRESS.md and continue from the next unfinished phase.
```

## Baad mein FAQs change karne hon
```
Replace data/faqs_seed.csv with the FAQs in [file name]. Keep the same columns,
re-seed the database, rebuild the TF-IDF and SBERT indexes, regenerate
test_queries.csv to match the new FAQs, rerun backend/nlp/evaluate.py, and
update docs/results/ and the test cases with the new numbers.
```
Ya admin dashboard se khud add/edit kar lein, ya CSV import button use karein.

## Folder mein kya hai
- `BUILD_PROMPT.md` — Claude Code ke liye poora build plan (7 phases)
- `CLAUDE.md` — project rules, Claude Code har session mein khud parhta hai
- `docs/dissertation_ch1-3.txt` — aapke Chapter 1–3
- `docs/report_template_structure.txt` — GIS6001 report ka template
- `docs/requirements.md` — FR/NF requirements (FR-01 ka text theek kar diya gaya hai)
- `backend/`, `frontend/`, `data/`, `diagrams/`, `screenshots/` — khaali folders, Claude Code bharega

## Report submit karne se pehle yaad rakhein
- FAQ data sample hai; asli college FAQs milne par replace karein, ya methodology mein
  "compiled from publicly available college websites" likhein.
- Chapter 2 se stray line hatayein: "The last month of training is October 2023."
- References verify karein (Al Emran 2020, Huang 2022, Perez 2020 ka text unke asli
  papers se match nahi karta; Bnedetto, MIT Stella, Al-Busaidi, Mohammed & Al-Rashdi check karein).
- Colleges ka naam Chapter 1 aur Chapter 3 mein same rakhein.
- Survey ke 30 responses asli logon se lein; Claude Code sirf questionnaire aur analysis script banayega.
