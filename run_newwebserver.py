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
    instance_name = input("Enter the name of your instance: ")
    key_path = make_key_read_only(utils.get_valid_key("Enter path to your private key: "))
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
                utils.get_security_group(),  # call util method to create or get security group id
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


# Function to wait till instance get's a public ip and returns the public ip
def wait_till_public_ip(instance):
    print ('Waiting for instance to get a public ip to access later')
    while not instance.public_ip_address:  # loop through till break condition (when the instance get's public ip)
        try:  # try block as instance may not immediately exist
            instance.reload()  # reload the instance property
            if instance.public_ip_address:  # if the created instance gets an public ip
                public_ip = instance.public_ip_address  # store the public ip for ssh later
                utils.print_and_log('Instance Public IP: ' + public_ip)
                return public_ip
        except Exception as error:
            utils.print_and_log(error)


# Simple check does ssh work by passing pwd to ssh command to instance
def check_ssh(public_ip, key_path):
    exit_loop = 0  # Loop control variable
    while exit_loop <= 10:  # Loop ssh command as can take a while for instance to be up after creation
        ssh_check_cmd = construct_ssh(key_path, public_ip, " 'sudo pwd'")
        (status, output) = subprocess.getstatusoutput(ssh_check_cmd)
        if status == 0:  # ssh command ran ok
            utils.print_and_log('Instance is ready to ssh')
            break
        elif 'bad permissions' in output:  # If key is not read only to you
            make_key_read_only(key_path)
        elif exit_loop == 10:  # On condition where loop has reach 10
            utils.print_and_log("Loop 10 reached - instance wasn't ready in time.. exiting loop")
            utils.print_and_log(output)
            break
        else:  # Increase exit_loop by 1 and sleep for 15 seconds before running ssh command again
            utils.print_and_log('Instance is not ready to ssh yet, trying again in 15 seconds - loop '
                                + str(exit_loop) + '/10')
            exit_loop += 1
            time.sleep(15)


# Copy check_webserver.py to instance using scp
def copy_check_webserver(public_ip, key_path):
    copy_check_web_server_cmd = 'scp -i ' + key_path + ' check_webserver.py ec2-user@' + public_ip + ':.'
    utils.print_and_log('Now trying to copy check_webserver to new instance with: ' + copy_check_web_server_cmd)
    (status, output) = subprocess.getstatusoutput(copy_check_web_server_cmd)
    if status == 0:  # if successfully copied, change permissions to make it executable
        utils.print_and_log('Successfully copied check_webserver.py to new instance')
        (status, output) = subprocess.getstatusoutput(construct_ssh(key_path, public_ip,
                                                                    " 'chmod 700 ./check_webserver.py'"))
        if status == 0:  # if successful, run check webserver
            run_check_webserver(public_ip, key_path)
        else:
            utils.print_and_log(str('Failed to change persmissions: ' + output))
    else:
        utils.print_and_log('Copy check_webserver.py failed :(')


# Run check_webserver.py on instance
def run_check_webserver(public_ip, key_path):
    utils.print_and_log('Now trying to run check_webserver in instance')
    exit_loop = 0  # Loop control variable
    while exit_loop <= 10:  # loop as can take a while for instance to be up and for scp copying
        ssh_run_check_cmd = construct_ssh(key_path, public_ip, " './check_webserver.py'")
        (status, output) = subprocess.getstatusoutput(ssh_run_check_cmd)
        if status == 0:  # Successfully ran ssh command
            utils.print_and_log('Successfully run the check_webserver.py on instance')
            utils.print_and_log(output)
            break
        elif 'Permission denied (publickey)' in output:  # If public key was wrong
            utils.print_and_log('Wrong key to ssh to instance')
            key_path = make_key_read_only(utils.get_valid_key('Re-enter path to key: '))
        elif exit_loop == 10:  # On the 10th loop
            if 'No such file or directory' in output:  # if there was no check_webserver on instance, ask to copy over
                utils.print_and_log('check_websever.py doesn\'t seem to be on instance')
                choice = input('Copy check_webserver to instance (y/n): ').lower()
                if choice == 'y':
                    copy_check_webserver(public_ip, key_path)
                else:
                    print ('Returning to main menu')
            elif '/usr/bin/python3: bad interpreter: No such file' in output:  # if python3 wasn't installed on instance
                utils.print_and_log('Python35 doesn\'t seem to on instance')
                install_python35(key_path, public_ip)  # install on instance and run loop again
                utils.print_and_log('Running run_check_webserver again')
                exit_loop = 0
            else:  # Otherwise exit loop
                utils.print_and_log('Exiting due to exit loop limit reached')
                utils.print_and_log(output)
                break
        else:  # increase loop variable by 1 and sleep for 15 seconds
            utils.print_and_log('Run check_webserver.py failed, trying again in 15 seconds - loop '
                                + str(exit_loop) + '/10')
            time.sleep(15)
            exit_loop += 1


# Create a new bucket
def create_bucket():
    while True:  # Loop as till break condition as bucket name must be unique
        bucket_name = input("\nBucket name: ").lower()  # bucket name must be all lower case
        try:
            response = s3.create_bucket(
                Bucket=bucket_name,  # create bucket with name and default region in aws config
                CreateBucketConfiguration={'LocationConstraint': utils.default_region()})
            utils.print_and_log(response)
            choice = input("Would you like to upload file to this bucket now (y/n): ")  # ask user to upload file
            if choice == 'y':  # if input is y
                put_file_in_bucket(bucket_name)
            else:  # otherwise break loop
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
            public_ip = get_instance_ip()
            if public_ip:  # If there is a public ip returned
                while True:
                    try:
                        key_path = make_key_read_only(utils.get_valid_key("Enter path to your private key: "))
                        change_index_file_permission(public_ip, key_path)
                        append_to_index(public_ip, url, key_path)
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
# Use echo to append to the bottom of the index.html
def append_to_index(public_ip, url, key_path):
    if url.endswith('.png') or url.endswith('.jpg') or url.endswith('.gif'):  # if the url is a common image format
        tag_url = '"<img src=\"' + url + '">\"'  # enclose html in img tags
    else:  # otherwise encase as a link with the url basename
        tag_url = '"<a href=\"' + url + '">' + os.path.basename(url) + '</a>\"'
    cmd = " 'sudo echo " + tag_url + " >> /usr/share/nginx/html/index.html'"  # compose bash command to pass by ssh

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


# List buckets and get file to upload if there are buckets
def list_and_upload_bucket():
    bucket_map = {}  # empty empty that will be used to map value to bucket name
    i = 1  # iterable vale that is used as key to bucket name dictionary value
    print ('#', '\tBucket Name')
    for bucket in s3.buckets.all():  # For each bucket the user owns
        bucket_map[str(i)] = bucket.name  # Map current i value as key to bucket name to dictonary
        print (str(i) + "\t" + bucket.name)
        i += 1  # increase i by 1
    if len(bucket_map) == 0:  # If dictionary if empty i.e have no buckets
        print ("You have no buckets. Create one at the main menu")
        time.sleep(3)
    else:  # Otherwise loop to get user input for bucket number to get bucket name from dictionary
        while True:
            try:
                choice = input("Enter number of bucket: ")
                put_file_in_bucket(bucket_map[choice])
                break
            except Exception as error:
                print ("Error: Not a valid option")


# List instances for running check server
def get_instance_ip():
    instance_dict = {}  # Create empty dictionary
    i = 1  # Value to iterate as key for dictonary
    ec2 = boto3.resource('ec2')
    print ('\n#', '\tInstance ID', '\t\tPublic IP Adrress')
    for instance in ec2.instances.all():
        if instance.state['Name'] == 'running':  # for only instances that are running
            instance_dict[str(i)] = instance.public_ip_address  # map current value of i as key to public address value
            print (i, '\t' + instance.id, '\t' + instance.public_ip_address)
            i += 1
    if len(instance_dict) == 0:  # if there are no instances running
        print ("You have no instances. Create one at the main menu")
        time.sleep(3)
    else:  # if there are running instances, get input from user to get instance public ip
        while True:
            try:
                choice = input("Enter number of instance: ")
                return instance_dict[choice]  # Get's public ip from dictionary and return
            except Exception as error:
                print ("Error: Not a valid option")


# Method to install python35 on instance on case where it wasn't installed for script to run
def install_python35(key_path, public_ip):
    install_cmd = construct_ssh(key_path, public_ip, " 'sudo yum install -y python35'")
    utils.print_and_log('Installing python35')
    (status, output) = subprocess.getstatusoutput(install_cmd)
    if status == 0:
        utils.print_and_log('Successfully installed python35')
    else:
        utils.print_and_log('Failed to install python35')
        utils.print_and_log(output)


# Get basic instance cpu info from instance
def get_instance_usage(key_path, public_ip):
    usage_cmd = construct_ssh(key_path, public_ip, " 'top -n 1 -b'")
    (status, output) = subprocess.getstatusoutput(usage_cmd)
    if status == 0:
        utils.print_and_log(output)
        time.sleep(5)
    else:
        utils.print_and_log('Get usage failed ' + output)


# Make key read only to you as otherwise would be ignored during ssh
def make_key_read_only(key_path):
    (status, output) = subprocess.getstatusoutput('stat -c "%a %n" ' + key_path)  # get file permission status
    if '600' not in output:  # if not 600, change file permission
        utils.print_and_log('Private key must by read only to you, othwerwise will be ignored')
        (status, output) = subprocess.getstatusoutput("chmod 600 " + key_path)
        if status == 0:
            utils.print_and_log("Change key to read only by you, to avoid ssh problems")
        else:
            utils.print_and_log("Failed to change key permissions to read only by you " + output)
    return key_path


# Main menu of script
def menu():
    print ('''
Welcome
    1. Create instance and bucket
    2. Create instance 
    3. Create bucket 
    4. Upload to bucket
    5. Run check_server on instance
    6. Print basic cpu usage on instance
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
            list_and_upload_bucket()
        elif choice == "5":
            try:
                public_ip = get_instance_ip()
                if public_ip:
                    key_path = make_key_read_only(utils.get_valid_key("Enter path to your private key: "))
                    run_check_webserver(public_ip, key_path)
            except Exception as error:
                utils.print_and_log("Run Check Server Error: " + str(error))
        elif choice == '6':
            try:
                public_ip = get_instance_ip()
                if public_ip:
                    key_path = make_key_read_only(utils.get_valid_key("Enter path to your private key: "))
                    get_instance_usage(key_path, public_ip)
            except Exception as error:
                utils.print_and_log("Get Instance Usage Error: " + str(error))
        elif choice == "0":
            print ("Exiting")
            sys.exit(0)
        else:
            print ("Not a valid choice")


# This is the standard boilerplate that calls the main() function.
if __name__ == "__main__":
    main()
