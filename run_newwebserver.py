#!/usr/bin/python3

import boto3
import base64

# UserData script - need to base64 encode string unless loaded from file (encoded by cli)
installNginx = base64.b64encode(b''' #!/bin/bash
yum -y update
yum install -y python35
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

print ('Id of newly create instance:' + instance[0].id)

createdInstanceId = instance[0].id  # Store the id of the created instance
instancePublicIp = ''

for instance in ec2.instances.all():  # Get all your instances and loop through them
    if instance.id == createdInstanceId:  # If the instance id is the newly created instance
        print ('Waiting for instance to start running')
        while True:  # loop through till break condition
            if instance.public_ip_address:  # if the created instance gets an public ip
                instancePublicIp = instance.public_ip_address  # store the public ip for ssh later
                print ('Public ip address of instance is: ', instancePublicIp)
                break

print ('Waiting for the instance to be pass checks, cannot ssh until then :(')

# Poll your new instance every 15 seconds until a successful state is reached.
# An error is returned after 40 failed checks.

client = boto3.client('ec2')
waiter = client.get_waiter('instance_status_ok')
waiter.wait(
    InstanceIds=[
        createdInstanceId,
    ]
)

print ('Instance has passed status checks and now can be accessed by ssh!!')
