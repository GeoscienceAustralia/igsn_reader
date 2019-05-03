import yaml
import os
import sys
import logging
import sqlite3
import re
import requests
from lxml import etree
from time import sleep
import abc

DEBUG_MAX_SAMPLES = 2500 # Number of samples to store before finishing while in debug mode
REPORT_INCREMENT = 1000 # Number of records to insert before reporting progress
MAX_RETRIES = 2 # Maximum number of times to retry request
RETRY_SLEEP = 2 # Seconds to sleep before retrying request

logger = logging.getLogger(__name__)

settings = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                                                 'igsn_reader_config.yml')))
if settings['debug']:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.debug('Logger {} set to level {}'.format(logger.name, logger.level))


class IGSNReader(object):
    
    def __init__(self):
        '''
        Constructor for IGSNReader class
        '''
        pass
                
    @abc.abstractmethod
    def read_igsns(self, oaipmh_source_list=None):
        '''
        Function to read IGSNS into database
        '''
        pass
