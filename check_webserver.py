#!/usr/bin/python3
import subprocess


# Function to start nginx (assuming it has been installed)
def start_nginx():
    start_cmd = 'sudo service nginx start'
    print('Going to start nginx with: ' + start_cmd)
    (status, output) = subprocess.getstatusoutput(start_cmd)
    if status == 0:
        print('Nginx is now up and running')
    elif 'nginx: unrecognized service' in output:
        install_nginx()
    else:
        print('Start nginx - something is wrong :(')
        print(status, output)


# Function to check is nginx running (assuming it has been installed)
def check_nginx():
    cmd = 'ps -A | grep nginx'
    (status, output) = subprocess.getstatusoutput(cmd)
    if status == 0:
        print('Nginx server is already running')
    else:
        print('Nginx server is NOT running' + str(output))
        start_nginx()


# Function to install nginx if not already installed
def install_nginx():
    print('Nginx not installed')
    choice = input('Install nginx (y/n): ').lower()
    if choice == 'y':
        install_cmd = 'sudo yum install -y nginx'
        (status, output) = subprocess.getstatusoutput(install_cmd)
        if status == 0:
            print('Nginx installed')
            start_nginx()
        else:
            print('Nginx install error')
            print(output)


# Main funcion
def main():
    check_nginx()


# This is the standard boilerplate that calls the main() function.
if __name__ == "__main__":
    main()
