'''
Created on 10 Apr 2019

@author: alex
'''

from pprint import pprint
from igsn_reader import IGSNReader
import sys
import logging

root_logger = logging.getLogger()


def main():
    igsn_reader = IGSNReader()
    pprint(igsn_reader.__dict__)
    
    igsn_reader.read_igsns()
    

if __name__ == '__main__':
    # Setup logging handlers if required
    if not root_logger.handlers:
        # Set handler for root root_logger to standard output
        console_handler = logging.StreamHandler(sys.stdout)
        #console_handler.setLevel(logging.INFO)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    main()