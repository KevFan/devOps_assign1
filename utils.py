import os
import sys


def get_abs_file_path(prompt):
    key_path = os.path.abspath(input(prompt))  # get user input of file path
    print ('File path: ' + key_path)
    while os.path.exists(key_path) is False:  # loop until the input is a valid path
        key_path = os.path.abspath(input("Path error - " + prompt))
    return key_path


def get_key_name_from_path(path):
    key_name = os.path.basename(path)  # get base name from absolute path passed in
    if key_name.endswith('.pem'):  # checks does the file end in a .pem extension
        return key_name.split('.')[0]
    else:
        sys.exit(1)
    # TODO: Need to check what happens if it doesnt end with a .pem extension and check does user have key in region


def get_rel_file_path(prompt):
    key_path = os.path.relpath(input(prompt))  # get user input of file path
    while os.path.exists(key_path) is False:  # loop until the input is a valid path
        key_path = os.path.relpath(input("Path error - " + prompt))
    return key_path
