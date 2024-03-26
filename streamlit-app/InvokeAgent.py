import boto3
from log_setup import logger
import json
import os

def lambda_handler(event, context):
    
    agentId = os.environ['AGENT_ID'] #INPUT YOUR AGENT ID HERE
    agentAliasId = os.environ['AGENT_ALIAS_ID'] # Hits draft alias, set to a specific alias id for a deployed version
    sessionId = event["sessionId"]
    question = event["question"]
    endSession = False
    
    logger.debug(f"Session: {sessionId} asked question: {question}")
    
    client = boto3.client('bedrock-agent-runtime')
    try:
        response = client.invoke_agent(
            agentId=agentId,
            agentAliasId=agentAliasId,
            sessionId=sessionId,
            endSession=False,
            enableTrace=False,
            inputText=question
            )
        resBody = response['completion']
        for line in resBody:
            answer = line['chunk']['bytes'].decode('utf-8')
        return { 
            "status_code": response['ResponseMetadata']['HTTPStatusCode'],
            "body": json.dumps({"response": answer})
        }
    except Exception as e:
        logger.debug(e)
        return {
            "status_code": 500,
            "body": json.dumps({"response": str(e)})  # "error": "Internal Server Error"
        }
