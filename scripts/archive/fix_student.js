const fs = require('fs');
let content = fs.readFileSync('backend/app/api/v1/student.py', 'utf8');

// Quiz generation
content = content.replace(
  'skip_entailment=True,   # Quiz generation — skip entailment',
  'skip_entailment=False,'
);

// Summary generation
content = content.replace(
  'skip_entailment=True,   # Summary generation — skip entailment',
  'skip_entailment=False,'
);

// We also need to update BestScoredSummaryResponse winner mapping
content = content.replace(
  'grounding=0.0,          # entailment skipped',
  'grounding=1.0 if s["entailment"] else 0.0,'
);

fs.writeFileSync('backend/app/api/v1/student.py', content);
console.log("student.py updated.");
