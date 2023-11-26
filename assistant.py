"""
A simple OpenAI Assistant with Functions, created by David Bookstaber.
The functions defined here in functions.py give the Assistant the ability to
    generate random numbers and strings, which is something a base Assistant cannot do.

This module is designed to be used by gui.py, which provides a minimal terminal consisting of
- an input textbox for the user to type a message for the assistant
- an output textbox to display the assistant's response

User/assistant interactions are also written to LOGFILE (AssistantLog.md).
The complete OpenAI interactions are encoded in JSON and printed to STDOUT.

When creating the assistant, this module also stores the Assistant ID in .env, so as
    to avoid recreating it in the future.  (A list of assistants that have been created
    with your OpenAI account can be found at https://platform.openai.com/assistants)

REQUIREMENT: You will need an OPENAI_API_KEY, which should be stored in .env
    See https://platform.openai.com/api-keys
"""
import json
import os
import time
import dotenv
from datetime import datetime
from openai import OpenAI
from functions import Functions
dotenv.load_dotenv()
OpenAI.api_key = os.getenv('OPENAI_API_KEY')
ASSISTANT_ID = os.getenv('ASSISTANT_ID')

LOGFILE = 'AssistantLog.md'  # We'll store all interactions in this file
AI_RESPONSE = '-AIresponse-'  # GUI event key for Assistant responses

def show_json(obj):
    """Formats JSON for more readable output."""
    return json.dumps(json.loads(obj.model_dump_json()), indent=2)

class Assistant:
    def __init__(self):
        while OpenAI.api_key is None:
            input("Hey! Couldn't find OPENAI_API_KEY. Put it in .env then press any key to try again...")
            dotenv.load_dotenv()
            OpenAI.api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI()
        self.run = None
        self.message = None
        global ASSISTANT_ID
        if ASSISTANT_ID is None:  # Create the assistant
            assistant = self.client.beta.assistants.create(
                name="Random Assistant",
                instructions="Format your responses in markdown.",
                model="gpt-4-1106-preview",
                tools=[{"type": "function", "function": Functions.get_random_digit_JSON},
                       {"type": "function", "function": Functions.get_random_letters_JSON}]
            )
            # Store the new assistant.id in .env
            dotenv.set_key('.env', 'ASSISTANT_ID', assistant.id)
            ASSISTANT_ID = assistant.id
        self.create_AI_thread()

    def create_AI_thread(self):
        """Creates an OpenAI Assistant thread, which maintains context for a user's interactions."""
        print('Creating assistant thread...')
        self.thread = self.client.beta.threads.create()
        print(show_json(self.thread))
        with open(LOGFILE, 'a+') as f:
            f.write(f'# {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\nBeginning {self.thread.id}\n\n')

    def wait_on_run(self, window):
        """Waits for an OpenAI assistant run to finish and handles the response."""
        print('Waiting for assistant response...')
        while self.run.status == "queued" or self.run.status == "in_progress":
            self.run = self.client.beta.threads.runs.retrieve(thread_id=self.thread.id, run_id=self.run.id)
            time.sleep(1)
        if self.run.status == "requires_action":
            print(f'\nASSISTANT REQUESTS {len(self.run.required_action.submit_tool_outputs.tool_calls)} TOOLS:')
            tool_outputs = []
            for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
                tool_call_id = tool_call.id
                name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                print(f'\nAssistant requested {name}({arguments})')
                output = getattr(Functions, name)(**arguments)
                tool_outputs.append({"tool_call_id": tool_call_id, "output": json.dumps(output)})
                print(f'\n\tReturning {output}')
            self.run = self.client.beta.threads.runs.submit_tool_outputs(thread_id=self.thread.id, run_id=self.run.id, tool_outputs=tool_outputs)
            self.wait_on_run(window)
        else:
            # Get messages added after our last user message
            new_messages = self.client.beta.threads.messages.list(thread_id=self.thread.id, order="asc", after=self.message.id)
            with open(LOGFILE, 'a+') as f:
                f.write('\n**Assistant**:\n')
                for m in new_messages:
                    f.write(m.content[0].text.value)
                f.write('\n\n---\n')
            # Callback to GUI with list of messages added after the user message we sent
            window.write_event_value(AI_RESPONSE, new_messages)

    def send_message(self, window, message_text: str):
        """
        Send a message to the assistant.

        Parameters
        ----------
        window : PySimpleGUI.window
            GUI element with .write_event_value() callback method, which will receive the Assistant's response.
        message_text : str
        """
        self.message = self.client.beta.threads.messages.create(self.thread.id,
                                                role = "user",
                                                content = message_text)
        print('\nSending:\n' + show_json(self.message))
        self.run = self.client.beta.threads.runs.create(thread_id=self.thread.id, assistant_id=ASSISTANT_ID)
        with open(LOGFILE, 'a+') as f:
            f.write(f'**User:** `{message_text}`\n')
        self.wait_on_run(window)
