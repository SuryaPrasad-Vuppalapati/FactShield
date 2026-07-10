const req = {
  question: "can you give me a hint on how to solve cost function?",
  doc_ids: ["123e4567-e89b-12d3-a456-426614174000"],
  chat_history: []
};

fetch("http://localhost:8000/api/v1/student/method-grounding", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(req)
})
.then(res => {
  console.log("Status:", res.status);
  return res.json();
})
.then(data => {
  console.log("Data:", data);
  console.log("data.text:", data.text);
})
.catch(err => console.error("Error:", err));
