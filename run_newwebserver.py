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
def create_instance():
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
    return instance[0]


# Function to wait till instance get's a public ip and returns the public ip
def wait_till_public_ip(instance):
    print ('Waiting for instance to get a public ip to access later')
    while True:  # loop through till break condition (when the instance get's public ip)
        instance.reload()  # reload the instance property
        if instance.public_ip_address:  # if the created instance gets an public ip
            public_ip = instance.public_ip_address  # store the public ip for ssh later
            print ('Instance Public IP: ', public_ip)
            return public_ip
            break


# Function to poll your new instance every 15 seconds until a successful state is reached using boto3 api
# An error is returned after 40 failed checks.
def wait_till_passed_checks(instance_id):
    print ('Waiting for instance to pass checks, cannot ssh until then :( , will take 2 minutes or longer')
    client = boto3.client('ec2')
    waiter = client.get_waiter('instance_status_ok')
    waiter.wait(
        InstanceIds=[
            instance_id,
        ]
    )
    print ('Instance has passed status checks and now can be accessed by ssh!!')


# Simple check does ssh work by passing pwd to ssh command to instance
def check_ssh(public_ip):
    ssh_check_cmd = "ssh -t -o StrictHostKeyChecking=no -i kfan-ohio.pem ec2-user@" + public_ip + " 'sudo pwd'"
    print ('Going to check does ssh work with simple pwd command on instance')
    (status, output) = subprocess.getstatusoutput(ssh_check_cmd)
    if status == 0:
        print ('Simple ssh test passed!!')
    else:
        print ('Simple ssh failed')
        print (status, output)


# Copy check_webserver.py to instance
def copy_check_webserver(public_ip):
    copy_check_web_server_cmd = 'scp -i kfan-ohio.pem check_webserver.py ec2-user@' + public_ip + ':.'
    print ('Now trying to copy check_webserver to new instance with: ' + copy_check_web_server_cmd)
    (status, output) = subprocess.getstatusoutput(copy_check_web_server_cmd)
    if status == 0:
        print ('Successfully copied check_webserver.py to new instance')
    else:
        print ('Copy check_webserver.py failed :(')


# Run check_webserver.py on instance
def run_check_webserver(public_ip):
    ssh_run_check_cmd = "ssh -t -o StrictHostKeyChecking=no -i kfan-ohio.pem ec2-user@" \
                     + public_ip + " './check_webserver.py'"
    print ('Now trying to run check_webserver in new instance with: ' + ssh_run_check_cmd)
    (status, output) = subprocess.getstatusoutput(ssh_run_check_cmd)
    if status == 0:
        print ('Successfully run the check_webserver.py on instance')
        print (status, output)
    else:
        print ('Run check_webserver.py failed')
        print (status, output)


# Main function
def main():
    # Variable to store instance as object so that do not need to keep referring to list
    created_instance = create_instance()
    instance_id = created_instance.id  # Store the id of the created instance
    print ('Id of newly create instance: ' + instance_id)
    instance_public_ip = wait_till_public_ip(created_instance)  # Used to eventually store the instance public ip
    wait_till_passed_checks(instance_id)
    check_ssh(instance_public_ip)
    copy_check_webserver(instance_public_ip)
    run_check_webserver(instance_public_ip)


# This is the standard boilerplate that calls the main() function.
if __name__ == "__main__":
    main()
