import json
import boto3
import os
import requests

def lambda_handler(event, context):
    
    messageBody = json.loads(event['Records'][0]['Sns']['Message'])
    sendingContact = messageBody['originationNumber']
    url = os.environ['API']
    prompt = messageBody['messageBody']
    
    #Make API Call
    try:
        payload = {
        "prompt": prompt
        }
        response = requests.post(url, json=payload)
        answer = response.json()['body']
        answer = json.loads(answer)['response']
    except Exception as e:
        answer = "Sorry we couldn't serve the request at this moment,\nPlease try again later !"
    
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
    
