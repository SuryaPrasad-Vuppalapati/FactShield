import re

with open("backend/app/factshield/best_scored.py", "r") as f:
    content = f.read()

content = content.replace("def best_scored_candidate", "async def best_scored_candidate")
content = content.replace("gen = generate_with_logprobs", "gen = await generate_with_logprobs")
content = content.replace("variants = generate_k_variants", "variants = await generate_k_variants")

with open("backend/app/factshield/best_scored.py", "w") as f:
    f.write(content)
