const fs = require('fs');
let content = fs.readFileSync('frontend/src/App.tsx', 'utf8');

// 1. Fix selfcheck wrapper
content = content.replace(
  'appendMessage("ai", res.feedback || "Sentence check completed. See details below:", { selfcheck: res.sentence_checks });',
  'appendMessage("ai", res.feedback || "Sentence check completed. See details below:", { selfcheck: res });'
);

// 2. Fix explainer wrapper
content = content.replace(
  'appendMessage("ai", "Generated verified concept explanation:", { explainer: res.winner });',
  'appendMessage("ai", "Generated verified concept explanation:", { explainer: res });'
);

// 3. Fix generator wrapper
content = content.replace(
  'appendMessage("ai", res.text || `Generated ${res.test_items.length} practice questions:`, { testItems: res.text ? undefined : res.test_items });',
  'appendMessage("ai", res.text || `Generated ${res.test_items.length} practice questions:`, { testItems: res });'
);

// 4. Fix selfcheck legacy fallback block
content = content.replace(
  '} else if (activeTool === "selfcheck" && msg.data.selfcheck) {\n      const checks = msg.data.selfcheck;\n      if (checks.length > 0) {\n        const avgScore = checks.reduce((acc: number, item: any) => acc + item.score, 0) / checks.length;\n        entailment = avgScore >= 0.6;\n        consistency = checks.every((item: any) => item.supported);\n        confidence = avgScore * 100;\n      }',
  '} else if (activeTool === "selfcheck" && msg.data.selfcheck) {\n      const checks = msg.data.selfcheck.sentence_checks || [];\n      if (checks.length > 0) {\n        const avgScore = checks.reduce((acc: number, item: any) => acc + item.score, 0) / checks.length;\n        entailment = avgScore >= 0.6;\n        consistency = checks.every((item: any) => item.supported);\n        confidence = avgScore * 100;\n      }'
);

// 5. Fix generator legacy fallback block
content = content.replace(
  '} else if (activeTool === "generator" && msg.data.testItems) {\n      const items = msg.data.testItems;\n      if (items.length > 0) {\n        const avgScore = items.reduce((acc: number, item: any) => acc + item.grounding_score, 0) / items.length;\n        entailment = avgScore >= 0.6;\n        consistency = true;\n        confidence = avgScore * 100;\n      }',
  '} else if (activeTool === "generator" && msg.data.testItems) {\n      const items = msg.data.testItems.test_items || [];\n      if (items.length > 0) {\n        const avgScore = items.reduce((acc: number, item: any) => acc + item.grounding_score, 0) / items.length;\n        entailment = avgScore >= 0.6;\n        consistency = true;\n        confidence = avgScore * 100;\n      }'
);

// 6. Fix selfcheck JSX map
content = content.replace(
  '{msg.data.selfcheck.map((item: any, idx: number) => (',
  '{(msg.data.selfcheck.sentence_checks || []).map((item: any, idx: number) => ('
);

// 7. Fix generator JSX map
content = content.replace(
  '{msg.data.testItems.map((item: any, idx: number) => (',
  '{(msg.data.testItems.test_items || []).map((item: any, idx: number) => ('
);

fs.writeFileSync('frontend/src/App.tsx', content);
console.log("App.tsx replaced correctly.");
