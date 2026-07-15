from ollama import Client

client = Client(
    host="https://ollama.com",
    headers={
        "Authorization": "Bearer eb80e66b396949a5845aa41f58806fb7.1UqhuK1tQJqPYkXt_4OZjcLg"
    }
)

response = client.chat(
    model="gpt-oss:120b",   # or another cloud model you have access to
    messages=[
        {
            "role": "user",
            "content": "Explain quantum computing in simple terms."
        }
    ]
)

print(response["message"]["content"])