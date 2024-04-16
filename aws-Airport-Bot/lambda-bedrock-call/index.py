import json
import boto3
import os

def lambda_handler(event, context):
    
    #Agent Configuration
    agentId = os.environ['AGENT_ID'] #INPUT YOUR AGENT ID HERE
    agentAliasId = os.environ['AGENT_ALIAS_ID'] # Hits draft alias, set to a specific alias id for a deployed version
    sessionId = "MySession"
    endSession = False
    prompt = json.loads(event['body'])['prompt']
    
    
    #Logic to invokeAgent
    try:
        bedrockClient = boto3.client('bedrock-agent-runtime')
        response = bedrockClient.invoke_agent(
            agentId=agentId,
            agentAliasId=agentAliasId,
            sessionId=sessionId,
            endSession=False,
            enableTrace=False,
            inputText=prompt
            )
        resBody = response['completion']
        for line in resBody:
            answer = line['chunk']['bytes'].decode('utf-8')
        return {
            "status_code": 200,
            "body": json.dumps({"response": answer})  
        }
    except Exception as e:
        return {
            "status_code": 500,
            "body": json.dumps({"response": "Sorry we couldn't serve the request at this moment,\nPlease try again later !"})  # "error": "Internal Server Error"
        }
