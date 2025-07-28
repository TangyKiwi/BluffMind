# Copyright (c) 2025 Kevin Lin
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
from enum import Enum
from ollama import chat as ollama_chat
from openai import OpenAI
from openai import InternalServerError
from dotenv import load_dotenv
import json

class APIType(Enum):
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
from enum import Enum
from ollama import chat as ollama_chat
from openai import OpenAI
from openai import InternalServerError
from dotenv import load_dotenv
import json

class APIType(Enum):
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"

class BLMPClient:
    def __init__(self, api_type=APIType.OPENROUTER, model=None):
        self.api_type = api_type
        if api_type == APIType.OPENROUTER:
            try:
                api_key=os.environ["OPENROUTER_API_KEY"]
            except KeyError:
                load_dotenv()
                api_key = os.environ.get("OPENROUTER_API_KEY")
                if not api_key:
                    raise ValueError("OPENROUTER_API_KEY not found in environment variables or .env file.")
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key
            )
            self.model = "meta-llama/llama-3.3-8b-instruct:free" if model is None else model
            return
        elif api_type == APIType.OLLAMA:
            self.model = "llama3.2" if model is None else model
            return

    def set_model(self, model):
        self.model = model

    def complete_chat(self, messages, response_format=None):
        if self.api_type == APIType.OPENROUTER:
            try:
                response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format=response_format
                    ) if response_format is not None else self.client.chat.completions.create(
                        model=self.model,
                        messages=messages
                    )
                return 0, response.choices[0].message.content
            except Exception as e:
                print(e)
                if hasattr(e, 'status_code'):  # Check for HTTP status code
                    return e.status_code, json.loads(str(e.body).translate(str.maketrans({"'": '"', '"': "'"})))
                else:
                    return -1, {"message": f"Non-HTTP error occurred: {str(e)}"}
        elif self.api_type == APIType.OLLAMA:
            try:
                response = ollama_chat(self.model, messages=messages, format=response_format) \
                    if response_format is not None else ollama_chat(self.model, messages=messages)
                return 0, response['message']['content']
            except Exception as e: # change to ollama specific exception
                print(e)
                return 1, str(e)
    
    def f_call(self, messages, tools=None):
        if self.api_type == APIType.OPENROUTER:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools
            ).choices[0].message

            return response
        elif self.api_type == APIType.OLLAMA:
            response = ollama_chat(self.model, messages=messages, tools=tools)
            return response['message']

    def __str__(self):
        return self.model

def system_message(content):
    return {'role': 'system', 'content': content}

def user_message(content):
    return {'role': 'user', 'content': content}

def assistant_message(content):
    return {'role': 'assistant', 'content': content}

def message_to_string(message):
    if isinstance(message, dict):
        return f"[{message['role']}]:\n{message['content']}"
    elif isinstance(message, str):
        return message
    elif isinstance(message, list):
        return "\n".join([message_to_string(m) for m in message])
    else:
        raise ValueError(f"Unsupported message type: {type(message)}")


