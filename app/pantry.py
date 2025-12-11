import os
from dotenv import load_dotenv
import requests
from helpers.pantry_wrapper import *
from helpers import *

load_dotenv()

pantry_id = os.getenv("PANTRY_ID")

try:
    init_data = {
        "prompt": "reply in markdown although unsafe markdown is also allowed so valid HTML",
        "messages": [
            {
                "title": "title",
                "content": "content",
                "aicontent": "aicontent",
                "summary": "summary",
            }
        ],
        "styles": ["yorha.min.css", "webfont.css"],
        "status": "migrated",
    }
    response = create_basket(
        pantry_id, "pythonanywhere.json", init_data, return_type="body"
    )
    # response = get_contents(pantry_id, 'pythonanywhere.json', return_type='body')
    print(response)
except:
    print("Error: call failed")
bind_to_globals(init_data)
# prompt = init_data[prompt]
print(status)
