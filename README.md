# Developer Operations - Assignment 1

```
Welcome
    1. Create instance and bucket
    2. Create instance 
    3. Create bucket 
    4. Upload to bucket
    5. Run check_server on instance
    6. Print basic cpu usage on instance
    ===================
    0. Exit

```

The overall objective of this assignment is to automate using Python 3 the process ofcreating, launching and monitoring a public-facing web server in the Amazon cloud. The web server will run on an EC2 instance and display some static content that is stored in S3.

## Pre-requisites
* [Boto3](http://boto3.readthedocs.io/en/latest/guide/quickstart.html)
* [AWS Cli](https://aws.amazon.com/cli/)
* [Python3](https://www.python.org/)

## Feature List
* run_newwebserver.py
    * Create instance and bucket
    * Upload to bucket
      * Append file url to a running instance to nginx index.html if installed  
    * Copy/Run check_server.py to instance
    * Basic instance cpu report using top command
* check_webserver.py
  * Checks and starts nginx if not running
  * If nginx is not installed, asks user to install
* logs messages to log.txt for record

## Getting started:
```
# Ensure boto3, python3 installed and aws config/credentials configured
git clone <this repo>
cd devOps_assign1
chmod 700 run_newwebserver.py
./run_newwebserver.py
```

Running these command will give the main script read, write and execution permissions and bring up menu for user interaction.

## Running tests
```
# In project directory
python3 TestMethods.py -v
```

Only 3 methods are tested as they do not accept input from user or interact with boto api 

## List of Software + Technologies Used
* [PyCharm](https://www.jetbrains.com/pycharm/) - Python IDE
* [Boto3](http://boto3.readthedocs.io/en/latest/guide/quickstart.html) - (AWS) SDK for Python
* [Python3](https://www.python.org/)
* [Pylint](https://www.pylint.org/) - Python source code analyzer

## Improvements
* Testing done most manually - not extensively tested using unittest
* Do not hard code value for ami id (currnetly Ireland region) which are region specific - would likely cause problems if user's default region is different
* Incorporate cloudwatch for instance monitoring 
* Incorporate ssh specific library such as paramiko for ssh to instance instead of using subprocess library


## Authors:
Kevin Fan ([KevFan](https://github.com/KevFan))

## Version/Date:
31st October 2017
