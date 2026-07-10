const fs = require('fs');

let content = fs.readFileSync('frontend/src/App.tsx', 'utf8');

// The line is: const scores = msg.data.scores;
content = content.replace(
  'const scores = msg.data.scores;',
  `const scores = msg.data.scores ||
    msg.data.grounding?.scores ||
    msg.data.challenge?.scores ||
    msg.data.selfcheck?.scores ||
    msg.data.sourceHunter?.scores ||
    msg.data.summary?.scores ||
    msg.data.explainer?.scores ||
    msg.data.testItems?.scores;`
);

fs.writeFileSync('frontend/src/App.tsx', content);
console.log('Fixed App.tsx scores reading.');
