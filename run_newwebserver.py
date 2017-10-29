#!/usr/bin/python3

import boto3
import subprocess
import utils
import os
import sys
import time

s3 = boto3.resource("s3")


# Creates a new ec2 instance - ImageId in the Ireland region - requires the config file to be set in eu-west-1
def create_instance():
    utils.clear_screen()
    # Get instance info from the user
    instance_name = input("Enter the name of your instance?: ")
    key_path = utils.get_valid_key("Enter path to your private key: ")
    key_name = utils.get_file_name_from_path(key_path)

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
        created_instance = instance[0]
        utils.print_and_log('Created instance Id: ' + created_instance.id)
        instance_public_ip = wait_till_public_ip(created_instance)  # Used to eventually store the instance public ip

        # Ssh related
        check_ssh(instance_public_ip, key_path)
        copy_check_webserver(instance_public_ip, key_path)
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


# Simple check does ssh work by passing pwd to ssh command to instance
def check_ssh(public_ip, key_path):
    ssh_check_cmd = construct_ssh(key_path, public_ip, " 'sudo pwd'")
    exit_loop = 0
    while exit_loop != 10:
        (status, output) = subprocess.getstatusoutput(ssh_check_cmd)
        if status == 0:
            utils.print_and_log('Instance is ready to ssh')
            break
        elif exit_loop == 5:
            utils.print_and_log("Exit loop code 5 reached - instance wasn't ready in time exiting loop")
            utils.print_and_log(output)
        else:
            utils.print_and_log('Instance is not ready to ssh yet, trying again in 15 seconds')
            exit_loop += 1
            time.sleep(15)


# Copy check_webserver.py to instance
def copy_check_webserver(public_ip, key_path):
    copy_check_web_server_cmd = 'scp -i ' + key_path + ' check_webserver.py ec2-user@' + public_ip + ':.'
    utils.print_and_log('Now trying to copy check_webserver to new instance with: ' + copy_check_web_server_cmd)
    (status, output) = subprocess.getstatusoutput(copy_check_web_server_cmd)
    if status == 0:
        utils.print_and_log('Successfully copied check_webserver.py to new instance')
        choice = input("Would you like to run check websever (y/n): ").lower()
        if choice == 'y':
            run_check_webserver(public_ip, key_path)
        else:
            utils.print_and_log("Exiting back to menu")
    else:
        utils.print_and_log('Copy check_webserver.py failed :(')


# Run check_webserver.py on instance
def run_check_webserver(public_ip, key_path):
    ssh_run_check_cmd = construct_ssh(key_path, public_ip, " './check_webserver.py'")
    utils.print_and_log('Now trying to run check_webserver in new instance with')
    exit_loop = 0
    while exit_loop != 10:
        (status, output) = subprocess.getstatusoutput(ssh_run_check_cmd)
        if status == 0:
            utils.print_and_log('Successfully run the check_webserver.py on instance')
            utils.print_and_log(output)
            break
        elif status == 10:
            utils.print_and_log('Exiting due to exit loop limit reached')
            utils.print_and_log(output)
        else:
            utils.print_and_log('Run check_webserver.py failed, trying again in 15 seconds')
            time.sleep(15)


# Create a new bucket
def create_bucket():
    while True:
        bucket_name = input("\nBucket name: ").lower()
        try:
            response = s3.create_bucket(Bucket=bucket_name,
                                        CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'})
            utils.print_and_log(response)
            choice = input("Would you like to upload file to this bucket now? (y/n)")
            if choice == 'y':
                put_file_in_bucket(bucket_name)
            else:
                utils.print_and_log("Returning back to main menu")
            break
        except Exception as error:
            utils.print_and_log(error)


# Puts a file into a bucket
def put_file_in_bucket(bucket_name):
    file_path = utils.get_abs_file_path('\nPath of file to put into bucket: ')  # get file name to upload to bucket
    try:  # set object name to just the base name as would otherwise create the folders to file.
        # Would have problems, especially when path to object is relative and when getting file link
        response = s3.Object(bucket_name, os.path.basename(file_path)).put(
            ACL='public-read',  # make public readable
            Body=open(file_path, 'rb'))
        utils.print_and_log(response)
        choice = input("Would you like to append file to index html (y/n): ").lower()
        if choice == 'y':
            url = get_file_url(bucket_name, os.path.basename(file_path))
            name_map = list_instances()
            if len(name_map) == 0:
                print ("You have no running instances to append to html")
            else:
                while True:
                    try:
                        public_ip = name_map[input("Enter number of instance: ")]
                        key_path = utils.get_valid_key("Enter path to your private key: ")
                        change_index_file_permission(public_ip, key_path)
                        append_image_to_index(public_ip, url, key_path)
                        break
                    except Exception as error:
                        print ("Error: Not a valid option")

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
    split = url.split('?')  # split url into a list at '?' as the above generates a url link that will be expired
    utils.print_and_log('Url: ' + split[0])
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


# Helper to construct ssh command to reduce duplication
def construct_ssh(key_path, public_ip, cmd):
    return "ssh -t -o StrictHostKeyChecking=no -i " + key_path + " ec2-user@" + public_ip + cmd


# List buckets for upload
def list_buckets():
    name_map = {}
    i = 1
    for bucket in s3.buckets.all():
        name_map[str(i)] = bucket.name
        print (str(i) + ": " + bucket.name)
        i += 1
    if len(name_map) == 0:
        print ("You have no buckets. Create one at the main menu")
        time.sleep(3)
    else:
        while True:
            try:
                choice = input("Enter number of bucket: ")
                put_file_in_bucket(name_map[choice])
                break
            except Exception as error:
                print ("Error: Not a valid option")


# List instances for running check server
def list_instances():
    name_map = {}
    i = 1
    ec2 = boto3.resource('ec2')
    print ('\n#', '\tInstance ID', '\t\tPublic IP Adrress')
    for instance in ec2.instances.all():
        if instance.state['Name'] == 'running':
            name_map[str(i)] = instance.public_ip_address
            print (i,  '\t' + instance.id, '\t' + instance.public_ip_address)
            i += 1
    return name_map


# Main menu of script
def menu():
    print ('''
Welcome
    1. Create instance and bucket
    2. Create instance 
    3. Create bucket 
    4. Upload to bucket
    5. Run check_server on instance
    ===================
    0. Exit''')


# Main function
def main():
    while True:
        menu()
        choice = input("\nEnter your choice: ")
        if choice == "1":
            print ("Create instance and bucket")
            create_instance()
            create_bucket()
        elif choice == "2":
            print ("Create instance")
            create_instance()
        elif choice == "3":
            print ("Create bucket")
            create_bucket()
        elif choice == "4":
            print ("Upload to bucket")
            list_buckets()
        elif choice == "5":
            name_map = list_instances()
            if len(name_map) == 0:
                print ("You have no instances running. Create one at the main menu")
                time.sleep(3)
            else:
                while True:
                    try:
                        choice = input("Enter number of instance: ")
                        key_path = utils.get_valid_key("Enter path to your private key: ")
                        run_check_webserver(name_map[choice], key_path)
                        break
                    except Exception as error:
                        print ("Error: Not a valid option")

        elif choice == "0":
            print ("Exiting")
            sys.exit(0)
        else:
            print ("Not a valid choice")


# This is the standard boilerplate that calls the main() function.
if __name__ == "__main__":
    main()
