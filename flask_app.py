
from flask import Flask, render_template, request, flash, redirect, url_for

from groq import Groq
from dotenv import load_dotenv
import os
#import google.generativeai as genai
from markdown2 import markdown as mdeee
from fuzzywuzzy import fuzz

load_dotenv()
# AI APIKey: Google Gemini
#genai.configure(api_key=os.getenv('GOOGLE_GEMINI_API'))
#genai.configure(api_key='apikeyinseralternative')

#model = genai.GenerativeModel('gemini-1.5-pro-latest')
#model = genai.GenerativeModel('gemini-1.0-pro')
model="llama-3.1-8b-Instant"

client = Groq(
    # This is the default and can be omitted
    api_key=os.environ.get("GROQ_API_KEY"),
)


app = Flask(__name__)

prompt = '(0. no javascript allowed 1. Write only in html or markdown format, using documentation from 2. pico css, .message-card is the class that can be changed, 3. jinja templates so additional pages can be created with the help of: 4. htmx in order to make local hx-swaps for dynamic effect and 5. alpinejs for boosting style and user interactivity) respond to: '


def ai(prompt, message):
  #googlegemini
    #response = model.generate_content(message)
 #  print(response.text)
  #return mdeee(response.text)

 #groq
  chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": message,
        }
    ],
    model=model,
  )
  reponse = chat_completion.choices[0].message
  return mdeee(reponse.content)


app = Flask(__name__)

messages = [{
    'title': 'Message One',
    'content': 'Message One Content',
    'aicontent': 'AI Generated Content'
}, {
    'title': 'Message Two',
    'content': 'Message Two Content',
    'aicontent': 'Message Three Content'
}]

@app.route('/')
def index():
 return render_template('create2.html', messages=messages)

@app.route('/create/', methods=['GET', 'POST'])
def create():
  if request.method == 'POST':
    title = request.form['title']
    content = request.form['content']
    aicontent = ai('', content)
    if not title:
      flash('Title is required!')
    elif not content:
      flash('Content is required!')
    else:
      messages.append({
          'title': title,
          'content': content,
          'aicontent': aicontent
      })
      # Redirect to the same page after successful submission
      return redirect(url_for('create'))

  return render_template('create.html', messages=messages)


@app.route('/create2/', methods=['GET', 'POST'])
def create2():
  if request.method == 'POST':
    title = request.form['title']
    content = request.form['content']
    aicontent = ai('', content)
    if not title:
      flash('Title is required!')
    elif not content:
      flash('Content is required!')
    else:
      messages.append({
          'title': title,
          'content': content,
          'aicontent': aicontent
      })
      # Redirect to the same page after successful submission
      return redirect(url_for('create2'))

  return render_template('create2.html', messages=messages)


@app.route('/submit_message', methods=['POST'])
def submit_message():
  # Process form data
  #title = request.form['title']
  content = request.form['content']
  title = str(len(messages))
  # Validate form data
  if not content:
    aicontent = ai("(provide an alternative to this approach): ",
                   messages[int(title) - 1]['content'])

  else:
    # Add message to the list
    aicontent = ai(prompt, content)

    messages.append({
        'title': title,
        'content': content,
        'aicontent': aicontent
    })

  # Render the updated message container HTML
  return render_template('message_card.html', message=messages[-1])


@app.route('/search', methods=['POST'])
def search():
  search_term = request.form['search']
  results_html = ""
  for message in reversed(messages):  # Iterate in reverse order
    if fuzz.partial_ratio(search_term.lower(), message['title'].lower()) >= 90 or \
  fuzz.partial_ratio(search_term.lower(), message['content'].lower()) >= 90 or \
  fuzz.partial_ratio(search_term.lower(), message['aicontent'].lower()) >= 50:
      results_html += f"""
            <div class="message-card">
                <!-- Add edit and favorite buttons here -->
                <div class="message-buttons">
                    <button class="edit-button">Edit</button>
                    <button class="favorite-button">★</button>
                </div>
                <div class="message-header">
                    <h3>{message['title']}</h3>
                </div>
                {message['aicontent']}
            </div>
            """
  return results_html


@app.route('/page')
def page():
  return render_template('page.html', messages=messages)

  # Code to make replit servers work
#if __name__ == '__main__':
#  app.run(host='0.0.0.0', port=8080)
