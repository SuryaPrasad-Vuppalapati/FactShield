import os
from google import genai
from app.schemas.chat import ChatMessage

def rewrite_query(message: str, chat_history: list[ChatMessage]) -> str:
    """Intelligently rewrites the user query using the conversation context."""
    if not chat_history:
        return message
        
    # Check if the last assistant message was a rejection.
    last_assistant_msg = ""
    for msg in reversed(chat_history):
        if msg.role == 'assistant':
            last_assistant_msg = msg.content
            break
            
    if "I couldn't find a clear answer" in last_assistant_msg:
        # Don't try to contextualize off of a failure.
        pass
        
    # Extract last few messages for context
    history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in chat_history[-6:]])
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return message

    prompt = (
        "You are an intelligent query rewriter for an educational AI. "
        "Your job is to read the chat history and the user's latest question, and rewrite the latest question so that it is completely self-contained and explicitly includes the subject matter being discussed.\n\n"
        f"Chat History:\n{history_text}\n\n"
        f"Latest Question: '{message}'\n\n"
        "If the latest question is a follow-up or relates to the previous topic, output the rewritten, self-contained question (e.g., 'What about for Logistic Regression?' -> 'How do I calculate the cost function for Logistic Regression?').\n"
        "If the latest question is completely new and unrelated to the chat history, just output the latest question exactly as it is.\n"
        "Return ONLY the rewritten string, no quotes, no markdown, no conversational filler."
    )
    
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        rewritten = response.text.strip().strip("'").strip('"')
        print(f"Query rewritten: '{message}' -> '{rewritten}'")
        return rewritten
    except Exception as e:
        print(f"Query Rewrite Error: {e}")
        return message
