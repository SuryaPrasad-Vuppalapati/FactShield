const fs = require('fs');

let content = fs.readFileSync('frontend/src/App.tsx', 'utf8');
content = content.replace(
  'console.log("AI TEXT:", res.text); appendMessage("ai", res.text || "TEXT WAS EMPTY OR UNDEFINED", { grounding: res });',
  'appendMessage("ai", "DEBUG DUMP: " + JSON.stringify(res), { grounding: res });'
);
fs.writeFileSync('frontend/src/App.tsx', content);
console.log("Added json dump debug.");
