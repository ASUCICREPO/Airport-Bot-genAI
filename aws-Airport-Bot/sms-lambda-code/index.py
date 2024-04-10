import json
import boto3
import os

def lambda_handler(event, context):
    
    messageBody = json.loads(event['Records'][0]['Sns']['Message'])
    sendingContact = messageBody['originationNumber']
    prompt = messageBody['messageBody']
    
    #Agent Configuration
    agentId = os.environ['AGENT_ID'] #INPUT YOUR AGENT ID HERE
    agentAliasId = os.environ['AGENT_ALIAS_ID'] # Hits draft alias, set to a specific alias id for a deployed version
    sessionId = "MySession"
    endSession = False
    
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
    except Exception as e:
        return {
            "status_code": 500,
            "body": json.dumps({"response": str(e)})  # "error": "Internal Server Error"
        }
    
    #Send the response back
    pinpoint = boto3.client('pinpoint')
    pinpoint.send_messages(
        ApplicationId='870b76a0545a46fbac20f66c5c0b389e',
        MessageRequest={
            'Addresses': {
                sendingContact: {'ChannelType': 'SMS'}
            },
            'MessageConfiguration': {
                'SMSMessage': {
                    'Body': answer,
                    'MessageType': 'PROMOTIONAL'
                }
            }
        }
    )
    
