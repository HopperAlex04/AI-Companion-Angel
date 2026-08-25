
## Accessing the API Docs

For detailed documentation and interactive usage of the API, visit the FastAPI docs at:

- `http://127.0.0.1:8000/docs`
```diff
# AI-Companion-Angel

[existing content]

# Run app (with ollama server running)
uvicorn main:app --reload


## API Usage Instructions

To interact with the API using `curl`, you can use the following command as a starting point:

curl -X POST http://127.0.0.1:8000/api/endpoint -H "Content-Type: application/json" -d '{"key": "value"}'

Where "endpoint" is the exact functionality you want. Currently this is detailed in the FastAPI docs.
