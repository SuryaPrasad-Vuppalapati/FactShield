const fs = require('fs');

let content = fs.readFileSync('frontend/src/App.tsx', 'utf8');

// 1. Fix summary block
const oldSummaryBlock = `                          {msg.data?.summary && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="winning-summary-text">
                                <div className="markdown-body">
                                  <ReactMarkdown>{msg.data.summary.winner.text}</ReactMarkdown>
                                </div>
                              </div>
                            </div>
                          )}`;

const newSummaryBlock = `                          {msg.data?.summary && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="winning-summary-text">
                                <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.9rem", color: "#333" }}>Optimal Summary</h4>
                                <div className="markdown-body">
                                  <ReactMarkdown>{msg.data.summary.winner.text}</ReactMarkdown>
                                </div>
                              </div>
                              {msg.data.summary.all_candidates?.length > 1 && (
                                <div className="alternative-summaries" style={{ marginTop: "1rem", borderTop: "1px solid #eee", paddingTop: "0.5rem" }}>
                                  <h5 style={{ margin: "0 0 0.5rem 0", fontSize: "0.85rem", color: "#666" }}>Alternative Candidates:</h5>
                                  {msg.data.summary.all_candidates.slice(1).map((cand: any, idx: number) => (
                                    <div key={idx} style={{ marginBottom: "0.5rem", padding: "0.5rem", background: "#f8f9fa", borderRadius: "4px", border: "1px solid #e9ecef" }}>
                                      <div style={{ display: "flex", gap: "12px", marginBottom: "6px", fontSize: "0.75rem", fontWeight: "600" }}>
                                        <span style={{ color: cand.grounding >= 0.5 ? "#2e7d32" : "#d32f2f" }}>Entailment: {cand.grounding >= 0.5 ? "Pass" : "Fail"}</span>
                                        <span style={{ color: cand.consistency >= 0.5 ? "#2e7d32" : "#d32f2f" }}>Consistency: {cand.consistency >= 0.5 ? "Pass" : "Fail"}</span>
                                        <span style={{ color: "#1976d2" }}>Confidence: {(cand.confidence * 100).toFixed(0)}%</span>
                                      </div>
                                      <div className="markdown-body" style={{ fontSize: "0.8rem", color: "#555" }}>
                                        <ReactMarkdown>{cand.text}</ReactMarkdown>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}`;

content = content.replace(oldSummaryBlock, newSummaryBlock);

// 2. Fix explainer block
const oldExplainerBlock = `                          {msg.data?.explainer && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="explanation-text">
                                <div className="markdown-body">
                                  <ReactMarkdown>{msg.data.explainer.text}</ReactMarkdown>
                                </div>
                              </div>
                            </div>
                          )}`;
// Notice msg.data.explainer.text was replaced. We need to use msg.data.explainer.winner.text, and also handle alternatives.
const newExplainerBlock = `                          {msg.data?.explainer && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="explanation-text">
                                <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.9rem", color: "#333" }}>Optimal Explanation</h4>
                                <div className="markdown-body">
                                  <ReactMarkdown>{msg.data.explainer.winner.text}</ReactMarkdown>
                                </div>
                              </div>
                              {msg.data.explainer.all_candidates?.length > 1 && (
                                <div className="alternative-summaries" style={{ marginTop: "1rem", borderTop: "1px solid #eee", paddingTop: "0.5rem" }}>
                                  <h5 style={{ margin: "0 0 0.5rem 0", fontSize: "0.85rem", color: "#666" }}>Alternative Explanations:</h5>
                                  {msg.data.explainer.all_candidates.slice(1).map((cand: any, idx: number) => (
                                    <div key={idx} style={{ marginBottom: "0.5rem", padding: "0.5rem", background: "#f8f9fa", borderRadius: "4px", border: "1px solid #e9ecef" }}>
                                      <div style={{ display: "flex", gap: "12px", marginBottom: "6px", fontSize: "0.75rem", fontWeight: "600" }}>
                                        <span style={{ color: cand.grounding >= 0.5 ? "#2e7d32" : "#d32f2f" }}>Entailment: {cand.grounding >= 0.5 ? "Pass" : "Fail"}</span>
                                        <span style={{ color: cand.consistency >= 0.5 ? "#2e7d32" : "#d32f2f" }}>Consistency: {cand.consistency >= 0.5 ? "Pass" : "Fail"}</span>
                                        <span style={{ color: "#1976d2" }}>Confidence: {(cand.confidence * 100).toFixed(0)}%</span>
                                      </div>
                                      <div className="markdown-body" style={{ fontSize: "0.8rem", color: "#555" }}>
                                        <ReactMarkdown>{cand.text}</ReactMarkdown>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}`;

if (content.includes('msg.data.explainer.text')) {
    content = content.replace(oldExplainerBlock, newExplainerBlock);
} else {
    // maybe it's msg.data.explainer.winner.text?
    const oldExplainerBlock2 = `                          {msg.data?.explainer && (
                            <div style={{ marginTop: "0.75rem" }}>
                              <div className="explanation-text">
                                <div className="markdown-body">
                                  <ReactMarkdown>{msg.data.explainer.winner.text}</ReactMarkdown>
                                </div>
                              </div>
                            </div>
                          )}`;
    content = content.replace(oldExplainerBlock2, newExplainerBlock);
}

fs.writeFileSync('frontend/src/App.tsx', content);
console.log("App.tsx UI updated.");
