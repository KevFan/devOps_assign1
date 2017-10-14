#!/usr/bin/python3

import boto3
import base64

# UserData script - need to base64 encode string unless loaded from file (encoded by cli)
installNginx = base64.b64encode(b''' #!/bin/bash
yum -y update
yum install -y nginx''')

# Creates a new ec2 instance - ImageId in the Ohio region
ec2 = boto3.resource('ec2')
instance = ec2.create_instances(
    ImageId='ami-c5062ba0',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.micro',
    # Name of the key to enable ssh
    KeyName='kfan-ohio',
    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'Nginx-Webserver'
                },
            ]
        },
    ],
    # Id of security group already created with http enabled
    SecurityGroupIds=[
        'sg-3e9a1056',
    ],
    UserData=installNginx
)
print (instance[0].id)
