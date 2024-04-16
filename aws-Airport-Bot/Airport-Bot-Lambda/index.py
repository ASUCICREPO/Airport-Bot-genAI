import requests
import json
import boto3
import os

headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Origin': 'https://www.jfkairport.com',
        'Referer': 'https://www.jfkairport.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }

def fetch_parking_data():
    url = 'https://avi-prod-mpp-webapp-api.azurewebsites.net/api/v1/parking/JFK'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json(),response.status_code
    else:
        return f"Failed to fetch data", response.status_code

def fetch_security_wait_times():
    url = 'https://avi-prod-mpp-webapp-api.azurewebsites.net/api/v1/SecurityWaitTimesPoints/JFK'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json(),response.status_code
    else:
        return f"Failed to fetch data", response.status_code


def get_taxi_wait_time():
    url = 'https://avi-prod-mpp-webapp-api.azurewebsites.net/api/v1/TaxiWaitTimePoints/JFK'
    modified_headers = headers
    modified_headers['Cookie'] = 'ARRAffinity=4999984147e99cda663c95c92db573f7557ccf48f3ef7c2bfe3c62d9ba510cae; ARRAffinitySameSite=4999984147e99cda663c95c92db573f7557ccf48f3ef7c2bfe3c62d9ba510cae'

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json(),response.status_code
    else:
        return "Error: Unable to fetch data",response.status_code

def get_walk_times():
    url = 'https://avi-prod-mpp-webapp-api.azurewebsites.net/api/v1/walkTimes/JFK'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json(),response.status_code
    else:
        return "Error: Unable to fetch data",response.status_code


def lambda_handler(event, context):
    #print("Received Event: ", event)
    
    apiPath = event["apiPath"]
    action = event["actionGroup"]
    httpMethod = event["httpMethod"]
    inputText = event["inputText"]
    parameters = event["parameters"]
    response_body = None
    
    if apiPath=="/static_data_query":
        
        #Logic to get response from kendra
        
        parameters = event.get('parameters', [])
        query = parameters[0].get('value') if parameters else None
    
        # Initialize the Kendra client
        if not query:
            return {'statusCode': 400, 'body': json.dumps("No query provided")}

        # Initialize the Kendra client
        kendra = boto3.client('kendra')
    
        # Define your Kendra index ID
        index_id = os.environ['KENDRA_INDEX_ID']
        
        try:
            # Query Kendra
            response = kendra.query( IndexId=index_id, QueryText=query)
            answer_text = ""
            counter = 0
            
            # Process the response as needed
            for query_result in response["ResultItems"]:
                answer_text += query_result["DocumentExcerpt"]["Text"]
                counter += 1
                if counter>10:
                    break
                
            response_code = 200
            response_body = {"application/json": {"body": answer_text }}
        except Exception as e:
            print(e)
            response_code = 400
            response_body = {"application/json": {"body": "Problem in fetching data !!"}}

        if response_body is None:
            response_body = {"application/json": {"body": "Can't find, please check the website." }}
        
    elif apiPath=="/parking_avail":
        parking_data, response_code = fetch_parking_data()
        terminal_to_find = event["parameters"][0]["value"]
        for inst in parking_data:
            terminal = inst["parkingLot"].split(' ')
            if terminal[0]=="Terminal":
                if terminal[1] == terminal_to_find:
                    response_body = {"application/json": {"body": inst["percentageOccupied"] }}
                    break
        if response_body is None:
            response_body = {"application/json": {"body": "Can't find, please check the website." }}
    elif apiPath=="/sec_wait_times":
        sec_data, response_code = fetch_security_wait_times()
        mapping = {
        "reg": "Reg",
        "general": "Reg",
        "regular": "Reg",
        "tsa": "TSAPre",
        "tsa preline": "TSAPre",
        "tsa pre check": "TSAPre",
        "precheck": "TSAPre",
        }
        
        for parameter in event["parameters"]:
            if parameter["name"] == "terminalID":
                terminal_to_find = parameter["value"]
            if parameter["name"] == "lineType":
                line_type = parameter["value"]
        
        for keyword, mapped_value in mapping.items():
            if keyword in line_type.lower():
                line_type = mapped_value
                break
        
        for inst in sec_data:
            if inst["terminal"] == terminal_to_find and inst["queueType"] == line_type and inst["queueOpen"] == True :
                response_body = {"application/json": {"body": inst["timeInMinutes"] }}
                break
        if response_body is None:
            response_body = {"application/json": {"body": "Can't find, please check the website." }}
            
    elif apiPath=="/walk_time_to_gates":
        response_code = 200
        for parameter in event["parameters"]:
            if parameter["name"] == "terminalID":
                terminal_to_find = parameter["value"]
            if parameter["name"] == "gateNumber":
                gate_number = parameter["value"]
        
        if terminal_to_find == "1":
            if 1 <= int(gate_number) < 5:
                response_body = {"application/json": {"body": "1-2" }}
            elif 5<= int(gate_number) <= 11:
                response_body = {"application/json": {"body": "3-4" }}
            else:
                pass
        elif terminal_to_find == "5":
            if int(gate_number) < 12 or (int(gate_number) > 17 and int(gate_number)<28):
                response_body = {"application/json": {"body": "2-4" }}
            elif 12 <= int(gate_number) <= 17 or 28 <= int(gate_number) <= 30:
                response_body = {"application/json": {"body": "5-7" }}
            else:
                pass
        elif terminal_to_find == "7":
            response_body = {"application/json": {"body": "1-2" }}
        elif terminal_to_find == "4":
            if gate_number.startswith("A") and gate_number >= "A3":
                response_body = {"application/json": {"body": "3-5" }}
            elif gate_number.startswith("B"):
                if gate_number >= "B1" and gate_number <= "B25":
                    response_body = {"application/json": {"body": "3-5" }}
                elif gate_number >= "B26" and gate_number <= "B33":
                    response_body = {"application/json": {"body": "7-11" }}
                elif gate_number >= "B34" and gate_number <= "B42":
                    response_body = {"application/json": {"body": "12-14" }}
                elif gate_number >= "B43" and gate_number <= "B55":
                    response_body = {"application/json": {"body": "15-18" }}
                else:
                    pass
            else:
                pass
        elif terminal_to_find == "8":
            if int(gate_number) >= 5 and int(gate_number) < 17:
                response_body = {"application/json": {"body": "2-4" }}
            elif (int(gate_number) >= 1 and int(gate_number) <= 4) or (int(gate_number) >= 40 and int(gate_number) <= 47):
                response_body = {"application/json": {"body": "5-8" }}
            elif gate_number >= "31" and int(gate_number) <= 39:
                response_body = {"application/json": {"body": "8-11" }}
            else:
                pass
        else:
            pass
        if response_body is None:
            response_body = {"application/json": {"body": "Can't find, please check the website." }}
        
    elif apiPath=="/taxi_wait_time":
        taxi_wait_time,response_code = get_taxi_wait_time()
        terminal_to_find = event["parameters"][0]["value"]
        
        for inst in taxi_wait_time:
            if inst["terminal"] == terminal_to_find:
                response_body = {"application/json": {"body": inst["timeInMinutes"] }}  
                break
        if response_body is None:
            response_body = {"application/json": {"body": "Can't find, please check the website." }}
        
    else:
        response_body = {"application/json": {"body": "Please ask relevant question"}}
        
    action_response = {
        "actionGroup": action,
        "apiPath": apiPath,
        "httpMethod": 'GET',
        "httpStatusCode": response_code,
        "responseBody": response_body,
    }

    # Return the list of responses as a dictionary
    api_response = {"messageVersion": "1.0", "response": action_response}
    return api_response
