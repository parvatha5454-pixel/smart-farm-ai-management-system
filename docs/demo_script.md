# Demo script (about 5 minutes)

Setup: `python seed.py --yes`, copy `.env.example` to `.env`, set `AI_API_KEY` and `FARM_LOCATION`, run `python app.py`.
Login: admin@farm.com / admin123.

1. **Dashboard** (30 s). Point out the "Recorded" vs "Forecast / suggestion" badges, overdue tasks, this month's expenses,
   the weather card (real Open-Meteo data, source shown).
2. **Copilot, read-only** (60 s). Click "How much did I spend this month?". Show the tool chip
   "Checking expenses: checked". Compare the number with the Expenses page: they match because the answer comes from the database.
3. **Copilot, advice** (60 s). Ask "Based on the weather forecast and my crops, should I review my irrigation schedule?".
   Show the "Facts" and "Recommendations" sections and the expert-verification reminder.
4. **Approval flow** (60 s). Ask "Create a task to check the water pump tomorrow, high priority".
   A proposal card appears. Open the Tasks page in another tab: nothing yet. Click Review and approve, then Yes. Refresh Tasks: it is there.
5. **Weekly planner** (45 s). Generate suggestions, show the reason column and the "Missing information" box, approve two, discard the rest.
6. **No-AI mode** (30 s). Remove `AI_API_KEY`, restart: the chat shows an honest setup message while quick buttons and the planner still work.
7. **Worker login** (30 s). ramesh@farm.com / worker123: only own tasks, no expense tool, no planner.
