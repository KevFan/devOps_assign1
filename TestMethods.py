import unittest
import os
from run_newwebserver import construct_ssh
from utils import get_file_name_from_path
from utils import print_and_log


# Test methods that do not accept input from user or interact with boto3 api
class TestMethods(unittest.TestCase):
    # Test construct ssh
    def test_construct_ssh(self):
        ssh = construct_ssh('/keys/key.pem', '192.168.0.1', " 'ls -l'")
        self.assertEqual(ssh, "ssh -t -o StrictHostKeyChecking=no -i /keys/key.pem ec2-user@192.168.0.1 'ls -l'")

    # Test get file name from path
    def test_get_file_name_from_path(self):
        path = os.path.abspath('./check_server.py')
        name = get_file_name_from_path(path)
        self.assertEqual(name, 'check_server')

    # Test print and log
    def test_print_and_log(self):
        print_and_log("Hello from test")  # will append and create if log.txt is not present
        self.assertTrue(True, os.path.exists(os.path.abspath('log.txt')))  # assert the path exists
        log_file = open("log.txt", "r")  # open log.txt
        temp_list = []
        for line in log_file:  # assign temp list to be the last line in log.txt
            temp_list = (line.split(' - '))  # split line at ' - ' to separate date and message
        self.assertEqual("Hello from test", temp_list[1])  # assert message are equal
        log_file.close()


if __name__ == '__main__':
    unittest.main()
