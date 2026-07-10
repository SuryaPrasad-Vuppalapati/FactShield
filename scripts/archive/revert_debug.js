const fs = require('fs');

let content = fs.readFileSync('frontend/src/App.tsx', 'utf8');
content = content.replace(
  'appendMessage("ai", "DEBUG DUMP: " + JSON.stringify(res), { grounding: res });',
  'appendMessage("ai", res.text, { grounding: res });'
);
fs.writeFileSync('frontend/src/App.tsx', content);
console.log("Reverted debug dump.");
