import requests
from dotenv import load_dotenv
import os


def get_chat_completion(input_text, model, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"

    # Prepare the headers
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Prepare the data payload
    data = {"messages": [{"role": "user", "content": input_text}], "model": model}

    # Perform the POST request
    response = requests.post(url, headers=headers, json=data)

    # Check if the request was successful
    if response.status_code == 200:
        # Deserialize the JSON response
        response_data = response.json()
        # Extract the content from the response
        return (
            response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


# Example usage
if __name__ == "__main__":
    load_dotenv()
    groq_api_key = os.getenv("GROQ_API_KEY")
    MODEL = "llama3-70B-8192"  # Replace with your desired model
    input_text = "Hello, how can I help you today?"

    result = get_chat_completion(input_text, MODEL, groq_api_key)
    print(result)
