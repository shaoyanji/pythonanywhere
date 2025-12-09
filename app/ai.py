import os
from dotenv import load_dotenv
import subprocess
import requests
import json

# import mysql.connector
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")
cohere_api_key = os.getenv("COHERE_API_KEY")

prompt = (
    "You are a helpful assistant and your output is only in markdown unsafe allowed"
)


def aiflow(prompt, message):
    return gemini_handler(prompt + message)


def groq_handler(message):
    load_dotenv()

    groq_api_key = os.getenv("GROQ_API_KEY")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "messages": [{"role": "user", "content": message}],
        "model": "llama3-70B-8192",
    }
    response = requests.post(url=url, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        return (
            response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return response_data


def cohere_handler(message):
    url = "https://api.cohere.com/v2/chat"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {cohere_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        # "temperature": 0.3,
        "model": "command-a-03-2025",
        "messages": [{"role": "user", "content": message}],
    }
    response = requests.post(url=url, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        return response_data.get("message", {}).get("content", {})[0].get("text", "")

    else:
        print(f"Error: {response.status_code} - {response.text}")
        return "api endpoints failed"


def gemini_handler(message):
    data_payload = {"contents": [{"parts": [{"text": message}]}]}
    data_json = json.dumps(data_payload)
    # bypassing some gemini refusal issues
    command = [
        "curl",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        "-H",
        f"x-goog-api-key: {gemini_api_key}",
        "-H",
        "Content-Type: application/json",
        "-X",
        "POST",
        "-d",
        data_json,
    ]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    if result.returncode == 0:
        try:
            response_data = json.loads(result.stdout)
            return (
                response_data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

        except json.JSONDecodeError:
            return "json decoder return failed on the response"
    else:
        return groq_handler(message)


def gptimage_handler(message):
    # command = [
    #     "tgpt",
    #     "--provider",
    #     "gemini",
    #     # "groq",
    #     "--key",
    #     gemini_api_key,
    #     # groq_api_key,
    #     # "--model",
    #     # "llama3-70b-8192",
    #     "-w",
    #     "-q",
    #     message,
    # ]
    command = ["tgpt", "--img", "-q", message]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return result.stdout
