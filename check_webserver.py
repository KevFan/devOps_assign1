#!/usr/bin/python3
import subprocess


# Function to start nginx (assuming it has been installed)
def start_nginx():
    startCmd = 'sudo service nginx start'
    print('Going to start nginx with: ' + startCmd)
    (status, output) = subprocess.getstatusoutput(startCmd)
    if status == 0:
        print ('Nginx is now up and running')
    else:
        print ('Start nginx - something is wrong :(')
        print (status, output)


# Function to check is nginx running (assuming it has been installed)
def check_nginx():
    cmd = 'ps -A | grep nginx'
    (status, output) = subprocess.getstatusoutput(cmd)
    if status == 0:
        print ('Nginx server is already running')
    else:
        print ('Nginx server is NOT running')
        start_nginx()


# Main funcion
def main():
    check_nginx()


if __name__ == "__main__":
    main()
