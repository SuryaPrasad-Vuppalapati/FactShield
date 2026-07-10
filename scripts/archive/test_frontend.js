const fs = require('fs');

let content = fs.readFileSync('frontend/src/App.tsx', 'utf8');
if (content.includes('console.log("AI TEXT:", res.text);')) {
  console.log("already debugged");
} else {
  content = content.replace(
    'appendMessage("ai", res.text, { grounding: res });',
    'console.log("AI TEXT:", res.text); appendMessage("ai", res.text || "TEXT WAS EMPTY OR UNDEFINED", { grounding: res });'
  );
  fs.writeFileSync('frontend/src/App.tsx', content);
  console.log("Added debug logging to frontend.");
}
