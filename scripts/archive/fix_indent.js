const fs = require('fs');

function fixFile(filename) {
    let content = fs.readFileSync(filename, 'utf8');
    let lines = content.split('\n');
    let newLines = [];
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];
        if (line.startsWith('    import asyncio')) {
            // Find how many spaces to remove
            line = line.replace(/^    /, '');
            newLines.push(line);
            // apply this offset to subsequent lines until the block ends
            i++;
            while (i < lines.length) {
                line = lines[i];
                if (line.trim() === '' || line.startsWith('    ')) {
                    newLines.push(line.replace(/^    /, ''));
                } else if (line.startsWith('return BestScoredSummaryResponse(') || line.startsWith('    return BestScoredSummaryResponse(')) {
                    newLines.push(line.replace(/^    /, ''));
                    break;
                } else {
                    newLines.push(line);
                }
                i++;
            }
        } else {
            newLines.push(line);
        }
    }
    fs.writeFileSync(filename, newLines.join('\n'));
}

fixFile('backend/app/api/v1/student.py');
fixFile('backend/app/api/v1/teacher.py');
console.log("Fixed indentation.");
