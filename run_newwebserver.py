#!/usr/bin/python3

import boto3
import subprocess
import utils
import os
import sys

s3 = boto3.resource("s3")


# Creates a new ec2 instance - ImageId in the Ireland region - requires the config file to be set in eu-west-1
def create_instance(instance_name, key_name):
    try:
        ec2 = boto3.resource('ec2')
        instance = ec2.create_instances(
            ImageId='ami-acd005d5',
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            KeyName=key_name,  # Name of the key to enable ssh
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': instance_name
                        },
                    ]
                },
            ],
            SecurityGroupIds=[
                'sg-8842b9f3',  # Id of security group already created with http & ssh enabled
            ],
            UserData='''#!/bin/bash
                        yum -y update
                        yum install -y python35
                        yum install -y nginx'''
        )
        utils.print_and_log('Created instance Id: ' + instance[0].id)
        return instance[0]
    except Exception as error:
        utils.print_and_log('Instance creation failed - exiting')
        utils.print_and_log(error)
        sys.exit(1)


# Function to wait till instance get's a public ip and returns the public ip
def wait_till_public_ip(instance):
    print ('Waiting for instance to get a public ip to access later')
    while not instance.public_ip_address:  # loop through till break condition (when the instance get's public ip)
        instance.reload()  # reload the instance property
        if instance.public_ip_address:  # if the created instance gets an public ip
            public_ip = instance.public_ip_address  # store the public ip for ssh later
            utils.print_and_log('Instance Public IP: ' + public_ip)
            return public_ip


# Function to poll your new instance every 15 seconds until a successful state is reached using boto3 api
# An error is returned after 40 failed checks.
# http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Waiter.InstanceStatusOk
def wait_till_passed_checks(instance_id):
    utils.print_and_log('Waiting for instance to pass checks, cannot ssh until then :( , will take 2 minutes or longer')
    client = boto3.client('ec2')
    waiter = client.get_waiter('instance_status_ok')
    waiter.wait(
        InstanceIds=[
            instance_id,
        ]
    )
    utils.print_and_log('Instance has passed status checks and now can be accessed by ssh!!')


# Simple check does ssh work by passing pwd to ssh command to instance
def check_ssh(public_ip, key_path):
    ssh_check_cmd = construct_ssh(key_path, public_ip, " 'sudo pwd'")
    utils.print_and_log('Going to check does ssh work with simple pwd command on instance')
    (status, output) = subprocess.getstatusoutput(ssh_check_cmd)
    if status == 0:
        utils.print_and_log('Simple ssh test passed!!')
    else:
        utils.print_and_log('Simple ssh failed')
        utils.print_and_log(output)
        sys.exit(1)


# Copy check_webserver.py to instance
def copy_check_webserver(public_ip, key_path):
    copy_check_web_server_cmd = 'scp -i ' + key_path + ' check_webserver.py ec2-user@' + public_ip + ':.'
    utils.print_and_log('Now trying to copy check_webserver to new instance with: ' + copy_check_web_server_cmd)
    (status, output) = subprocess.getstatusoutput(copy_check_web_server_cmd)
    if status == 0:
        utils.print_and_log('Successfully copied check_webserver.py to new instance')
    else:
        utils.print_and_log('Copy check_webserver.py failed :(')


# Run check_webserver.py on instance
def run_check_webserver(public_ip, key_path):
    ssh_run_check_cmd = construct_ssh(key_path, public_ip, " './check_webserver.py'")
    utils.print_and_log('Now trying to run check_webserver in new instance with: ' + ssh_run_check_cmd)
    (status, output) = subprocess.getstatusoutput(ssh_run_check_cmd)
    if status == 0:
        utils.print_and_log('Successfully run the check_webserver.py on instance')
        utils.print_and_log(output)
    else:
        utils.print_and_log('Run check_webserver.py failed')
        utils.print_and_log(output)


# Create a new bucket
def create_bucket():
    while True:
        bucket_name = input("Bucket name: ").lower()
        try:
            response = s3.create_bucket(Bucket=bucket_name,
                                        CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'})
            utils.print_and_log(response)
            return bucket_name
        except Exception as error:
            utils.print_and_log(error)


# Puts a file into a bucket
def put_file_in_bucket(bucket_name, object_name):
    try:  # set object name to just the base name as would otherwise create the folders to file.
        # Would have problems, especially when path to object is relative and when getting file link
        response = s3.Object(bucket_name, os.path.basename(object_name)).put(
            ACL='public-read',  # make public readable
            Body=open(object_name, 'rb'))
        utils.print_and_log(response)
    except Exception as error:
        utils.print_and_log(error)


# Returns the url of a object in a bucket
# https://stackoverflow.com/questions/43973658/how-to-access-image-by-url-on-s3-using-boto3
# http://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Client.generate_presigned_url
def get_file_url(bucket_name, object_name):
    client = boto3.client('s3')
    url = client.generate_presigned_url('get_object',
                                        Params={
                                            'Bucket': bucket_name,
                                            'Key': object_name,
                                        },
                                        ExpiresIn=3600)
    utils.print_and_log(url)
    split = url.split('?')  # split url into a list at '?' as the above generates a url link that will be expired
    return split[0]  # Return the url with no expiry date


# Change the file permission for write access of index.html - needed to echo into file for image appending later
def change_index_file_permission(public_ip, key_path):
    ssh_permission_cmd = construct_ssh(key_path, public_ip, " 'sudo chmod 646 /usr/share/nginx/html/index.html'")
    utils.print_and_log('Trying to change permission on index.html')
    (status, output) = subprocess.getstatusoutput(ssh_permission_cmd)
    if status == 0:
        utils.print_and_log('Successfully changed the file permission')
    else:
        utils.print_and_log('Failed to change file permission')
        utils.print_and_log(output)


# Append image uploaded to bucket to the end of index.html of nginx
def append_image_to_index(public_ip, image_url, key_path):
    # Use echo to append to the bottom of the index.html
    str = '"<img src=\"' + image_url + '">\"'  # enclose html in img tags

    cmd = " 'sudo echo " + str + " >> /usr/share/nginx/html/index.html'"  # compose bash command to pass by ssh

    ssh_cmd = construct_ssh(key_path, public_ip, cmd)
    utils.print_and_log('Now trying to append image url to index html with: ' + ssh_cmd)
    (status, output) = subprocess.getstatusoutput(ssh_cmd)
    if status == 0:
        utils.print_and_log('Successfully appended to index ')
    else:
        utils.print_and_log('Image append failed')
        utils.print_and_log(output)


def construct_ssh(key_path, public_ip, cmd):
    return "ssh -t -o StrictHostKeyChecking=no -i " + key_path + " ec2-user@" + public_ip + cmd


# Main function
def main():
    # Variable to store instance as object so that do not need to keep referring to list
    try:
        # Get instance info from the user
        instance_name = input("Enter the name of your instance?: ")
        key_path = utils.get_valid_key("Enter path to your private key: ")
        key_name = utils.get_file_name_from_path(key_path)

        # Create instance related
        created_instance = create_instance(instance_name, key_name)
        instance_id = created_instance.id  # Store the id of the created instance
        instance_public_ip = wait_till_public_ip(created_instance)  # Used to eventually store the instance public ip
        wait_till_passed_checks(instance_id)

        # Ssh related
        check_ssh(instance_public_ip, key_path)
        copy_check_webserver(instance_public_ip, key_path)
        run_check_webserver(instance_public_ip, key_path)

        # Bucket related
        created_bucket_name = create_bucket()  # create bucket with predefined name and returns name
        file_path = utils.get_abs_file_path('Path of file to put into bucket: ')  # get file name to upload to bucket
        put_file_in_bucket(created_bucket_name, file_path)  # upload to file to bucket

        # Image appending
        change_index_file_permission(instance_public_ip, key_path)
        append_image_to_index(instance_public_ip,
                              get_file_url(created_bucket_name, os.path.basename(file_path)), key_path)
    except Exception as error:
        utils.print_and_log(error)


# This is the standard boilerplate that calls the main() function.
if __name__ == "__main__":
    main()
