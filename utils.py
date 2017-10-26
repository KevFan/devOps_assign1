import os
import sys
import boto3


# Returns the absolute path to a file with a simple loop to check that the file exists
def get_abs_file_path(prompt):
    key_path = os.path.abspath(input(prompt))  # get user input of file path
    print ('File path: ' + key_path)
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
        print (error)
        return False


# Get relative path to a file - Unused
def get_rel_file_path(prompt):
    key_path = os.path.relpath(input(prompt))  # get user input of file path
    while os.path.exists(key_path) is False:  # loop until the input is a valid path
        key_path = os.path.relpath(input("Path error - " + prompt))
    return key_path


# Asks user to get input path to key for ssh
# Key is checked and only returns if valid
def get_valid_key(prompt):
    key_path = os.path.abspath(input(prompt))  # get user input of file path
    exit_boolean = False
    while exit_boolean is False:
        print ('File path: ' + key_path)
        # check does file exist
        if os.path.exists(key_path) is False:
            key_path = os.path.abspath(input("Path does not exist - " + prompt))
        # check does file is a .pem file
        if key_path.endswith('.pem') is False:
            key_path = os.path.abspath(input("Expecting .pem file - " + prompt))
        # check the user has key with the name in default region
        if check_user_has_key(os.path.basename(key_path).split('.')[0]) is False:
            key_path = os.path.abspath(input("Re-" + prompt))
        if key_path.endswith('.pem') and check_user_has_key(os.path.basename(key_path).split('.')[0]) \
                and os.path.exists(key_path):
            exit_boolean = True
            print ("Your key is valid !!")
    return key_path
