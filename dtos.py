from pydantic import BaseModel

class PromptItem(BaseModel):
    prompt_text: str
    conversation_id: int

class ConversationCreate(BaseModel):
    title: str
