import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
mongodb_uri = os.getenv("MONGODB_URI")

client = MongoClient(mongodb_uri)
db = client["boot"]
collection = db["users"]

app = FastAPI()

class ChatRequest(BaseModel):
    user_id: str
    question: str
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that advises users on fitness and health."),
    ("placeholder", "{history}"),
    ("user", "{question}")
])

llm = ChatGroq(api_key=groq_api_key, model="openai/gpt-oss-20b")
chain = prompt | llm

user_id = "321"

def get_user_history(user_id):
    chat = collection.find({"user_id": user_id}).sort("timestamp", 1)
    history = []
    for entry in chat:
        if entry["role"] == "user":
            history.append(("user", entry["question"]))
        elif entry["role"] == "assistant":
            history.append(("assistant", entry["response"]))
    return history

@app.get("/")
def read_root():
    return {"message": "Welcome to the fitness assistant API"}
@app.post("/chat")
def chat(request: ChatRequest):
    history = get_user_history(request.user_id)

    response = chain.invoke({
        "history": history,
        "question": request.question
    })
    

    # Save user message
    collection.insert_one({
        "user_id": request.user_id,
        "role": "user",
        "question": request.question,
        "response": None,
        "timestamp": datetime.now()
    })

    # Save assistant response
    collection.insert_one({
        "user_id": request.user_id,
        "role": "assistant",
        "question": request.question,
        "response": response.content,
        "timestamp": datetime.now()
    })

    return {"response": response.content}
