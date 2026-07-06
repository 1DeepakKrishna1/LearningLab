import sys
import requests
import json
from rich import print as rprint
from rich.pretty import Pretty
from rich.console import Console

from rich.markdown import Markdown

# logger
from telemetry_setup import setup_telemetry, app_logger
setup_telemetry()



#BASE_URL = "https://az-cenind-jspchbt-dev-appservice-phase1-eqdxb0exb7e7hqb6.centralindia-01.azurewebsites.net"
BASE_URL = "https://az-cenind-jspchbt-dev-appservice-phase1-eqdxb0exb7e7hqb6.centralindia-01.azurewebsites.net"
API_KEY = "API_KEY1"


def authenticate():
    """
    Step 1: Call /authenticate API
    Step 2: Extract JWT token
    """
    url = f"{BASE_URL}/api/v1/authenticate"

    payload = {
        "tenant": "string"
        # add other default fields here if required by API
    }

    headers = {
        "Content-Type": "application/json",
        "Api-Key": API_KEY
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    token = response.json().get("token")
    if not token:
        raise Exception("Token not found in response")

    print("✅ Authentication successful")
    return token

def get_auth_headers(token):
    """
    Step 2: Use JWT as HTTP Bearer
    """
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def start_conversation(token, message):
    url = f"{BASE_URL}/api/v1/conversation"

    payload = {
        "message": message
        # add optional fields like user_id, metadata if supported
    }

    headers = get_auth_headers(token)
    response = requests.post(url, json=payload, headers=headers)
    print("Trace ID:", response.headers["x-trace-id"])
    response.raise_for_status()

    return response.json()

def continue_conversation(token, message, conversation_id):
    url = f"{BASE_URL}/api/v1/conversation"

    payload = {
        "message": message
        # "conversation_id": conversation_id
        # add optional fields like user_id, metadata if supported
    }

    headers = get_auth_headers(token)
    response = requests.post(url, json=payload, headers=headers)
    trace_id = response.headers["x-trace-id"]
    print(f"Trace ID: {trace_id}")
    app_logger.info(f"Trace ID: {trace_id}, Input={message}")
    response.raise_for_status()

    return response.json()

def end_conversation(token, conversation_id):
    url = f"{BASE_URL}/api/v1/conversation/end"
    headers = get_auth_headers(token)

    payload = {
        "conversation_id": conversation_id
        # add optional fields like user_id, metadata if supported
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    return response.json()

def submit_feedback(token, message_id, rating, comments=None):
    url = f"{BASE_URL}/api/v1/conversation/userfeedback/{message_id}"

    payload = {
        "rating": rating,        # e.g., 1–5
        "comments": comments
    }

    headers = get_auth_headers(token)
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    return response.json()

def get_conversation_summary(token, conversation_id):
    url = f"{BASE_URL}/api/v1/conversation/summary?conversation_id={conversation_id}"
    headers = get_auth_headers(token)
    
    payload = {
        "conversation_id": conversation_id
        # add optional fields like user_id, metadata if supported
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()

def is_json(data):
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def main_console():
    try:
        token = authenticate()
        console = Console()

        # 1. Start conversation
        print(">>> User >>>: List of Jindal Products")
        inputQuery = "List of Jindal Products"
        convo_response = start_conversation(token, inputQuery)
        print(">> AI BOT >>:")
        #print(json.dumps(convo_response, indent=2))
        #rprint(Pretty(convo_response, expand_all=True))

        pMessage1 = convo_response["message"]["message"].replace("\\n", "").replace("\\", "").replace("\n", "")
        pMessage =  json.loads(pMessage1) if is_json(pMessage1) else convo_response["message"]
        # Render beautifully with Markdown
        console.rule("[bold green]Beautified Message[/bold green]")
        try:
            console.print(Markdown(pMessage["message"])) # folow_up
            #for follow_up in pMessage["follow_up"]:
            #    console.print(Markdown(follow_up))
        except:
            print(convo_response)


        conversation_id = convo_response.get("conversation_id")
        message_id = convo_response.get("message_id")

        # 1. Continue conversation
        inputMessage = input(">>> User >>>: ")
        while inputMessage not in ["exit", "end", "quit"]:
            try:
                convo_response = None
                convo_response = continue_conversation(token, inputMessage, conversation_id)
                print(">> AI BOT >>:")
                #print(json.dumps(convo_response, indent=2))
                #rprint(Pretty(convo_response, expand_all=True))
                pMessage1 = convo_response["message"]["message"].replace("\\n", "").replace("\\", "").replace("\n", "")
                pMessage =  json.loads(pMessage1) if is_json(pMessage1) else convo_response["message"]

                # Render beautifully with Markdown
                # console.rule("[bold green]Beautified Message[/bold green]")
                app_logger.info(f"Input={inputMessage}")
                app_logger.info(f"Bot Response={pMessage["message"]}")
                console.print(Markdown(pMessage["message"])) # folow_up
                #for follow_up in pMessage["follow_up"]:
                #    console.print(Markdown(follow_up))
                ## console.print(Markdown(pMessage["folow_up"]))
               
            except Exception as e:
                print(f"An error occurred: {e}")
                print(convo_response)

            inputMessage = input(">>>: ")

        # 2. Submit feedback
        if message_id:
            feedback_response = submit_feedback(
                token,
                message_id,
                rating=5,
                comments="Very helpful response"
            )
            print("\nFeedback Submitted:")
            print(json.dumps(feedback_response, indent=2))

    # 3. End conversation
        if conversation_id:
            end_resp = end_conversation(token, conversation_id)
            print("\nConversation Ended:")
            print(json.dumps(end_resp, indent=2))

        # 4. Get summary
        if conversation_id:
            summary = get_conversation_summary(token, conversation_id)
            print("\nConversation Summary:")
            print(json.dumps(summary, indent=2))

       

    except Exception as e:
        print("❌ Error:", str(e))


def main_test(preMessage, testCaseList):
    try:
        token = authenticate()
        console = Console()

        # 1. Start conversation
        print(">>> User >>>: Hi")
        inputQuery = "Hi"
        convo_response = start_conversation(token, inputQuery)
        print(">> AI BOT >>:")
        #print(json.dumps(convo_response, indent=2))
        #rprint(Pretty(convo_response, expand_all=True))

        pMessage1 = convo_response["message"]["message"].replace("\\n", "").replace("\\", "").replace("\n", "")
        pMessage =  json.loads(pMessage1) if is_json(pMessage1) else convo_response["message"]
        # Render beautifully with Markdown
        console.rule("[bold green]Beautified Message[/bold green]")
        try:
            console.print(Markdown(pMessage["message"])) # folow_up
            #for follow_up in pMessage["follow_up"]:
            #    console.print(Markdown(follow_up))
        except:
            print(convo_response)


        conversation_id = convo_response.get("conversation_id")
        message_id = convo_response.get("message_id")

        # 1. Continue conversation
        for inputMessage in testCaseList:
            try:
                print(">>> User >>>:" + inputMessage.strip())
                convo_response = None
                convo_response = continue_conversation(token, preMessage + inputMessage, conversation_id)
                print(">> AI BOT >>:")
                #print(json.dumps(convo_response, indent=2))
                #rprint(Pretty(convo_response, expand_all=True))
                pMessage1 = convo_response["message"]["message"].replace("\\n", "").replace("\\", "").replace("\n", "")
                pMessage =  json.loads(pMessage1) if is_json(pMessage1) else convo_response["message"]

                # Render beautifully with Markdown
                # console.rule("[bold green]Beautified Message[/bold green]")
                # app_logger.info(f"Input={inputMessage}")
                app_logger.info(f"Bot Response={pMessage["message"]}")
                console.print(Markdown(pMessage["message"])) # folow_up
                #for follow_up in pMessage["follow_up"]:
                #    console.print(Markdown(follow_up))
                ## console.print(Markdown(pMessage["folow_up"]))
               
            except Exception as e:
                print(f"An error occurred: {e}")
                print(convo_response)

        # 2. Submit feedback
        if message_id:
            feedback_response = submit_feedback(
                token,
                message_id,
                rating=5,
                comments="Very helpful response"
            )
            print("\nFeedback Submitted:")
            print(json.dumps(feedback_response, indent=2))

    # 3. End conversation
        if conversation_id:
            end_resp = end_conversation(token, conversation_id)
            print("\nConversation Ended:")
            print(json.dumps(end_resp, indent=2))

        # 4. Get summary
        if conversation_id:
            summary = get_conversation_summary(token, conversation_id)
            print("\nConversation Summary:")
            print(json.dumps(summary, indent=2))

       

    except Exception as e:
        print("❌ Error:", str(e))



def read_all_lines(file_path):
    """
    Reads all lines from the given text file and returns them as a list.

    :param file_path: Path to the input text file
    :return: List of lines
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.readlines()


def main():
    # Ensure file path is provided from CLI
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file_path>")
        # sys.exit(1)
        main_console()
        return

    input_file = sys.argv[1]
    preMessage = sys.argv[2]

    testCaseList = read_all_lines(input_file)
    main_test(preMessage,testCaseList)


if __name__ == "__main__":
    main()
