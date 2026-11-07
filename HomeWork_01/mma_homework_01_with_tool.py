import requests
import os
import json
import ast
from pprint import pprint
from dotenv import load_dotenv
load_dotenv(override=True)

# Load environments from the project
openai_api_key = os.environ.get("OPENAI_API_KEY")
openai_api_url = os.environ.get("OPENAI_API_URL")
openai_model = os.environ.get("OPENAI_MODEL")
openai_system_role = os.environ.get("OPENAI_SYSTEM_ROLE")
log_level = os.environ.get("LOG_LEVEL")
run_hw = os.environ.get("RUN_HW", "False").strip().lower() == "true"

# Questions used for HW (Hardcoded)
QUESTIONS = [
    {"id": 0, "text": "Calculate (123 + 22) multiple 3 and power by 2"},
    {"id": 1, "text": "Add 123 and 22"},
    {"id": 2, "text": "Multiple previous result by 3"},
    {"id": 3, "text": "Previous result power 2"},
    {"id": 4, "text": "Multiple 145 by 3"},
    {"id": 5, "text": "435 power 2"},
    {"id": 6, "text": "Substract 100 from first result"}
]

def get_question_by_id(qid: int) -> str | None:
    for q in QUESTIONS:
        if q["id"] == qid:
            return q["text"]
    return None
       
# Header
headers = {
    "Content-Type": "application/json", 
    "Authorization": f"Bearer {openai_api_key}"
}

# Tools 
def tool_add(a: float, b: float) -> float:
    return a + b


def tool_multiple(a: float, b: float) -> float:
    return a * b

def tool_power(a: float, b: float) -> float:
    return a ** b
    
# Define custom tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "tool_add",
            "description": "Add 2 numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_multiple",
            "description": "Multiple 2 numbers",
            "parameters": {
                "type": "object",
                "properties": {
                   "a": {"type": "number", "description": "First number"},
                   "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_power",
            "description": "Calculates a power (base to exponent)",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "base"},
                    "b": {"type": "number", "description": "exponent"}
                },
                "required": ["a", "b"],
            },
        },
    }
]    
 
available_functions = {
    "tool_add": tool_add,
    "tool_multiple": tool_multiple,
    "tool_power": tool_power
}

def printLog(log: str):
    if log_level in ("TRACE", "DEBUG"):
        print(f"{log}")
    return


# Call LLM API 
def call_llm_with_message(message: str, use_tools: bool = False):
    printLog(f">>> call_llm_with_message: ({message})")

    # Body
    data = {
        "model": openai_model,
        "messages": message
    }
    
    if use_tools:
        data["tools"] = tools
        data["tool_choice"] = "auto"
    
    response = requests.post(
        openai_api_url, headers=headers, json=data
    )
    
    printLog(f"Response: {response.json()}");
    printLog(f"<<< call_llm_with_message: (JSON)")
    return response.json()


def call_llm(question: str, use_tools: bool = False, messages: list = None):
    printLog(f">>> call_llm: ({question})")
    print(f"Question: ({question})")
    if messages is None:
        messages = [
            {"role": "system", "content": openai_system_role},
            {"role": "user", "content": question},
        ]
    else:
        messages.append({"role": "user", "content": question})

    while True:
        response = call_llm_with_message(messages, use_tools)
        choice = response["choices"][0]
        msg = choice["message"]

        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            content = msg.get("content") or ""
            printLog(f"<<< call_llm: ({content})")
            return messages

        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])
            tool_id = tool_call["id"]

            print(f"Tool: {function_name}({function_args})")

            if function_name in available_functions:
                try:
                    function_response = available_functions[function_name](**function_args)
                except Exception as e:
                    function_response = f"Error: {e}"
            else:
                function_response = f"Unknown function: {function_name}"

            print(f"Tool response: {function_response}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "name": function_name,
                "content": str(function_response)
            })

def request_to_steps_by_llm(question: str):
    printLog(f">>> request_to_steps_by_llm: ({question})")

    planner_messages = [
        {
            "role": "system",
            "content": (
                "You are a planner. Break the task into the smallest possible steps. "
                "Each step must be executable with one of these tools: tool_add, tool_multiple, tool_power. "
                "Return ONLY valid JSON (or Python dict) in this format:"
                "{'steps': ['step 1', 'step 2', ...]}"
                "Do not add any extra text."
            )
        },
        {"role": "user", "content": question}
    ]

    response = call_llm_with_message(planner_messages, use_tools=False)
    content = response["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        plan = ast.literal_eval(content)
        steps = plan["steps"]
    except Exception as e:
        print("Problem with parsing:", e)
        print("Raw answer:", content)
        return

    messages = None
    for i, step in enumerate(steps, 1):
        print(f"--- Step {i}: {step} ---")
        messages = call_llm(step, use_tools=True, messages=messages)

    printLog("<<< request_to_steps_by_llm")
    return


######################
###### STARTUP #######
######################
if __name__ == "__main__":

    print(f"###########################################################################")
    print(f"## Description: Homework for lesson 1 #####################################")
    print(f"## Author: Michal Madlenak ################################################")
    print(f"## Email: michalmadlenak@gmail.com ########################################")
    print(f"###########################################################################")
    
    print("\n")
    print("\n")
    print(f"###########################################################################")
    print(f"## RUN REQUESTS ONE BY ONE NO HISTORY WITH TOOLS ##########################")
    print(f"###########################################################################")
    call_llm(get_question_by_id(1), True)
    call_llm(get_question_by_id(4), True)
    call_llm(get_question_by_id(5), True)

    if not run_hw:
        print("\n")
        print("\n")
        print(f"###########################################################################")
        print(f"## RUN REQUESTS ONE BY ONE NO HISTORY NO TOOL #############################")
        print(f"###########################################################################")
        call_llm(get_question_by_id(1))
        call_llm(get_question_by_id(4))
        call_llm(get_question_by_id(5))
        
        print("\n")
        print("\n")
        print(f"###########################################################################")
        print(f"## RUN REQUESTS ONE BY ONE WITH HISTORY NO TOOL ###########################")
        print(f"###########################################################################")
        msg = call_llm(get_question_by_id(1))
        msg = call_llm(get_question_by_id(2), False, msg)
        msg = call_llm(get_question_by_id(3), False, msg)
        call_llm(get_question_by_id(6), False, msg)
            
        print("\n")
        print(f"###########################################################################")
        print(f"## SPLIT REQUEST TO SMALLER TASKS WITH TOOLS ##############################")
        print(f"###########################################################################")
        print("\n")
        request_to_steps_by_llm(get_question_by_id(0))