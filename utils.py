import os
import datetime
import boto3
import subprocess


# Returns the absolute path to a file with a simple loop to check that the file exists
def get_abs_file_path(prompt):
    key_path = os.path.abspath(input(prompt))  # get user input of file path
    print_and_log('File path: ' + key_path)
    while os.path.exists(key_path) is False:  # loop until the input is a valid path
        key_path = os.path.abspath(input("Path error - " + prompt))
    return key_path


# Get's file name from a path by getting the base name and removing the file extension
def get_file_name_from_path(path):
    file_name = os.path.basename(path)  # get base name from absolute path passed in
    return file_name.split('.')[0]


# Function that checks is user have a key with a key_name in their default region
def check_user_has_key(key_name):
    try:
        ec2 = boto3.client('ec2')
        response = ec2.describe_key_pairs(
            KeyNames=[
                key_name,
            ])
        if response:  # Assumes key is valid if the key_name matches, will throw error if it doesn't
            return True
    except Exception as error:
        print_and_log(error)
        return False


# Asks user to get input path to key for ssh
# Key is checked and only returns if valid
def get_valid_key(prompt):
    key_path = os.path.abspath(input(prompt))  # get user input of file path
    exit_boolean = False
    while exit_boolean is False:
        print_and_log('File path: ' + key_path)
        # check does file exist
        if os.path.exists(key_path) is False:
            key_path = os.path.abspath(input("Path does not exist - " + prompt))
        # check does file is a .pem file
        if key_path.endswith('.pem') is False:
            key_path = os.path.abspath(input("Expecting .pem file - " + prompt))
        # check the user has key with the name in default region
        if check_user_has_key(os.path.basename(key_path).split('.')[0]) is False:
            key_path = os.path.abspath(input("Re-" + prompt))
        # If key satisfies all the conditions above - exit loop
        if key_path.endswith('.pem') and check_user_has_key(os.path.basename(key_path).split('.')[0]) \
                and os.path.exists(key_path):
            exit_boolean = True
            print_and_log("Key is valid in this region")
    return key_path


# Helper function to print a message and write message to log file with a date time
def print_and_log(message):
    print (str(message))
    with open("log.txt", "a") as log_file:
        log_file.write('\n' + str(datetime.datetime.now()) + ' - ' + str(message))


# Clear the terminal
def clear_screen():
    tmp = subprocess.call('clear', shell=True)  # assign to variable so that 0 doesnt display to terminal


# Get default region is aws config
def default_region():
    # open aws config file - require os.path.expanduser to recognise ~
    f = open(os.path.expanduser('~/.aws/config'), 'rU')
    for line in f:
        if 'region' in line:  # if line contains region
            split = line.split('=')  # slit the line at = as the delimiter
            return split[1].strip()  # return the second word in list and devoid of whitespace
