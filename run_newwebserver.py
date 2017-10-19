#!/usr/bin/python3

import boto3
import base64
import subprocess

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
    KeyName='kfan-ohio',  # Name of the key to enable ssh
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
    SecurityGroupIds=[
        'sg-3e9a1056',  # Id of security group already created with http & ssh enabled
    ],
    UserData=installNginx
)

createdInstance = instance[0]  # Variable to store instance as object so that do not need to keep referring to list
instanceId = createdInstance.id  # Store the id of the created instance
instancePublicIp = ''  # Used to eventually store the instance public ip
print ('Id of newly create instance:' + instanceId)

print ('Waiting for instance to get a public ip to access later')
while True:  # loop through till break condition (when the instance get's public ip)
    createdInstance.reload()  # reload the instance property
    if createdInstance.public_ip_address:  # if the created instance gets an public ip
        instancePublicIp = createdInstance.public_ip_address  # store the public ip for ssh later
        print ('Public ip address of instance is: ', instancePublicIp)
        break

# Poll your new instance every 15 seconds until a successful state is reached.
# An error is returned after 40 failed checks.
print ('Waiting for the instance to be pass checks, cannot ssh until then :( , will take about 2 minutes')
client = boto3.client('ec2')
waiter = client.get_waiter('instance_status_ok')
waiter.wait(
    InstanceIds=[
        instanceId,
    ]
)
print ('Instance has passed status checks and now can be accessed by ssh!!')

# Simple check does ssh work by passing pwd to ssh command to instance
sshCheckCmd = "ssh -t -o StrictHostKeyChecking=no -i kfan-ohio.pem ec2-user@" + instancePublicIp + " 'sudo pwd'"
print ('Going to check does ssh work with simple pwd command on instance')
(status, output) = subprocess.getstatusoutput(sshCheckCmd)
if status == 0:
    print ('Simple ssh passed!!.: ' + output)
else:
    print ('Simple ssh failed')
    print (status, output)

# Copy check_webserver.py to instance
copyCheckWebServerCmd = 'scp -i kfan-ohio.pem check_webserver.py ec2-user@' + instancePublicIp + ':.'
print ('Now trying to copy check_webserver to new instance with: ' + copyCheckWebServerCmd)
(status, output) = subprocess.getstatusoutput(copyCheckWebServerCmd)
if status == 0:
    print ('Successfully copied check_webserver.py to new instance')
else:
    print ('Copy check_webserver.py failed :(')

# Run check_webserver.py on instance
sshRunCheckCmd = "ssh -t -o StrictHostKeyChecking=no -i kfan-ohio.pem ec2-user@" \
                 + instancePublicIp + " './check_webserver.py'"
print ('Now trying to run check_webserver in new instance with: ' + sshRunCheckCmd)
(status, output) = subprocess.getstatusoutput(sshRunCheckCmd)
if status == 0:
    print ('Successfully run the check_webserver.py on instance')
    print (status, output)
else:
    print ('Run check_webserver.py failed')
    print (status, output)
