with open("NEXT_PHASE_PLAN.md", "r") as f:
    text = f.read()

text = text.replace("- Add transformation-aware regime signals", "- [x] Add transformation-aware regime signals")
text = text.replace("- Separate slow structural scores", "- [x] Separate slow structural scores")
text = text.replace("- Keep portfolio/trade conclusions outside", "- [x] Keep portfolio/trade conclusions outside")

with open("NEXT_PHASE_PLAN.md", "w") as f:
    f.write(text)
