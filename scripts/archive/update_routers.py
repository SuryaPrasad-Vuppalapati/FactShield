import os

for fpath in ["backend/app/api/v1/student.py", "backend/app/api/v1/teacher.py"]:
    with open(fpath, "r") as f:
        content = f.read()

    # Replace chat_history=request.chat_history, with chat_history=request.chat_history, doc_ids=[request.doc_id] or doc_ids=request.doc_ids
    # We can just do a regex
    import re
    
    # Cases with request.doc_ids
    content = re.sub(
        r"(chat_history=request\.chat_history,\n\s*)\)",
        r"\1doc_ids=getattr(request, 'doc_ids', [getattr(request, 'doc_id', None)]),\n    )",
        content
    )

    with open(fpath, "w") as f:
        f.write(content)
        
print("Updated routers to pass doc_ids.")
