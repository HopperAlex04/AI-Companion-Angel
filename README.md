
## Accessing the API Docs

For detailed documentation and interactive usage of the API, visit the FastAPI docs at:

- `http://127.0.0.1:8000/docs`
```diff
# AI-Companion-Angel

[existing content]

# Run app (with llama server running)
# llama-server must be started with --jinja so OpenAI-style tool calls work
# (Gemma may use llama.cpp's generic tool handler if it has no native template)
uvicorn main:app --reload --port 8000 and uvicorn chat_service:app --reload --port 8001


## API Usage Instructions

To interact with the API using `curl`, you can use the following command as a starting point:

curl -X POST http://127.0.0.1:8000/api/endpoint -H "Content-Type: application/json" -d '{"key": "value"}'

Where "endpoint" is the exact functionality you want. Currently this is detailed in the FastAPI docs.
