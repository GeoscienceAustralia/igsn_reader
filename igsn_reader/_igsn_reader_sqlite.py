import os
import logging
import sqlite3
import re
import requests
from lxml import etree
from time import sleep

from ._igsn_reader import settings, IGSNReader

DEBUG_MAX_SAMPLES = 2500 # Number of samples to store before finishing while in debug mode
REPORT_INCREMENT = 1000 # Number of records to insert before reporting progress
MAX_RETRIES = 2 # Maximum number of times to retry request
RETRY_SLEEP = 2 # Seconds to sleep before retrying request

logger = logging.getLogger(__name__)

if settings['debug']:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.debug('Logger {} set to level {}'.format(logger.name, logger.level))

class IGSNReader_SQLite(IGSNReader):
    
    def __init__(self):
        '''
        Constructor for IGSNReader class
        '''
        super(IGSNReader_SQLite, self).__init__()
        
        self.sqlite_db_path = (settings.get('sqlite_db_path') 
                               or os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                                               'data', 'igsn_db.sqlite'))
        
        if not os.path.isfile(self.sqlite_db_path):
            self.db_connection = sqlite3.connect(self.sqlite_db_path)
            cursor = self.db_connection.cursor()
            
            ddl_sql_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                                        'data', 'igsn_reader_sqlite_ddl.sql')
            
            ddl_sql_file = open(ddl_sql_path, 'r')
            script_sql = ddl_sql_file.read()
            ddl_sql_file.close()
            
            # Strip comments using non-greedy regex substitutions
            script_sql = re.sub('--.*?$', '', re.sub('/\*.*?\*/', '', script_sql, flags=re.DOTALL), flags=re.MULTILINE)
            
            ddl_queries = [ddl_query.strip() + ';\n' for ddl_query in script_sql.split(';') if ddl_query.strip()]
            
            logger.info('Executing DDL script {}'.format(ddl_sql_path))
            for ddl_query in ddl_queries:
                logger.debug('Executing query:\n{}'.format(ddl_query))
                cursor.execute(ddl_query)
                self.db_connection.commit()

        else:
            self.db_connection = sqlite3.connect(self.sqlite_db_path)
            cursor = self.db_connection.cursor()
            
        for key, value in settings['oai_pmh_endpoints'].items():
            cursor.execute("""insert or ignore into OAIPMH (OAIPMH_KEY, OAIPMH_URL)
                values (?, ?);
                """, (key, value))
            self.db_connection.commit()
            if cursor.rowcount:
                logger.info('"{}" inserted into OAIPMH table for key {}'.format(value, key))
                
                
    def read_igsns(self, oaipmh_source_list=None):
        '''
        Function to read IGSNS into database
        '''
        print('blah')
        insert_sql = '''insert or ignore into sample (
    OAIPMH_ID,
    IDENTIFIER,
    DATESTAMP,
    ALT_IDENTIFIERS,
    TITLE,
    SUBJECT,
    DESCRIPTION,
    TYPE,
    FORMAT,
    COVERAGE,
    CREATOR,
    PUBLISHER,
    RIGHTS
    )
values (
    :oaipmh_id,
    :identifier,
    :datestamp,
    :alt_identifiers,
    :title,
    :subject,
    :description,
    :type,
    :format,
    :coverage,
    :creator,
    :publisher,
    :rights
    );
'''                        

        cursor = self.db_connection.cursor()
        cursor.execute('select OAIPMH_ID, OAIPMH_KEY, OAIPMH_URL from OAIPMH')
        
        for oaipmh_id, oaipmh_key, oaipmh_url in cursor.fetchall():
            # Skip any sources not in specified source list
            if oaipmh_source_list and oaipmh_key not in oaipmh_source_list:
                continue
            
            logger.debug('Querying records for {}'.format(oaipmh_key))
            
            http_params = {'verb': 'ListRecords',
                           'metadataPrefix': 'oai_dc',
                           'resumptionToken': None}
        
            sample_count = 0            
            resumption_token = None
            while not sample_count or resumption_token:
                logger.debug('resumption_token = {}'.format(resumption_token))
                if resumption_token:
                    http_params = {'verb': 'ListRecords',
                                   'resumptionToken': resumption_token}
                    
                retries = 0
                try:
                    response = requests.get(oaipmh_url, headers=None, params=http_params, data=None, timeout=settings['timeout'])
                    assert response.status_code == 200, 'Response status code {} != 200: {}'.format(response.status_code, response.content)
                    
                    # Hack to get around CSIRO namespace definition
                    response_content = response.content.decode('utf-8')
                    response_content = re.sub('xmlns:ns3="http://www.openarchives.org/OAI/2.0/"', '', re.sub('ns3:', '', response_content)).encode('utf-8')
                    #logger.debug(response_content)
                    
                    response_tree = etree.fromstring(response_content)
                    
                    list_records_element = response_tree.find('./ListRecords', namespaces=response_tree.nsmap)
                    if list_records_element is None:
                        logger.debug('Unable to find OAI-PMH/ListRecords element')
                        resumption_token = None
                        #print(response_content)
                        break
                except Exception as e:
                    logger.warning('HTTP get failed: {}'.format(e))
                    retries += 1
                    if retries <= MAX_RETRIES:
                        logger.warning('Waiting {} seconds before retrying...'.format(RETRY_SLEEP))
                        sleep(RETRY_SLEEP)
                        continue
                    else:
                        raise(e)
                                        
                resumption_token_element = list_records_element.find('./resumptionToken', namespaces=response_tree.nsmap)
                if resumption_token_element is not None:
                    resumption_token = resumption_token_element.text
                    if resumption_token is not None:
                        resumption_token = resumption_token.strip()
                else:
                    resumption_token = None
                
                # Read Dublin Core metadata for each record in response
                for record_element in list_records_element.findall('./record', namespaces=response_tree.nsmap):
                    insert_params = {'oaipmh_id': oaipmh_id}
                    try:
                        insert_params['identifier'] = record_element.find('./header/identifier', namespaces=response_tree.nsmap).text
                        try:
                            insert_params['datestamp'] = record_element.find('./header/datestamp', namespaces=response_tree.nsmap).text
                        except:
                            insert_params['datestamp'] = None
                            
                        # Find Dublin Core element
                        dc_element = record_element.find('./metadata/{http://www.openarchives.org/OAI/2.0/oai_dc/}dc', namespaces=response_tree.nsmap) # CSIRO
                        if dc_element is None:
                            dc_element = record_element.find('./metadata', namespaces=response_tree.nsmap) # GA
                        
                        insert_params['alt_identifiers'] = ', '.join([alt_identifier_element.text
                                                    for alt_identifier_element in dc_element.findall('./dc:identifier', 
                                                                                                     namespaces=dc_element.nsmap)
                                                    ])
                        
                        for dc_attribute in [
                            'title',
                            'subject',
                            'description',
                            'date',
                            'type',
                            'format',
                            'coverage',
                            'creator',
                            'publisher',
                            'rights',
                            ]:
                            try:                         
                                insert_params[dc_attribute] = dc_element.find('./dc:{}'.format(dc_attribute), 
                                                                                namespaces=dc_element.nsmap).text
                            except Exception as e:
                                #logger.debug('Dublin Core attribute read for {} failed: {}'.format(dc_attribute, e))
                                insert_params[dc_attribute] = None
                            
                        logger.debug('Inserting record for {}'.format(insert_params['identifier']))
                        insert_cursor = self.db_connection.cursor()
                        insert_cursor.execute(insert_sql, insert_params)
                        self.db_connection.commit()
                        sample_count += 1
                        
                        if sample_count % REPORT_INCREMENT == 0:
                            logger.info('{} samples updated'.format(sample_count))
                        
                        if settings['debug'] and sample_count == DEBUG_MAX_SAMPLES:
                            break
                        
                    except Exception as e:
                        logger.warning('Attribute read failed: {}'.format(e))
                        continue
                
                if settings['debug'] and sample_count >= DEBUG_MAX_SAMPLES:
                    logger.debug('Debug limit reached')
                    break

                        
            logger.info('{} samples updated for {}'.format(sample_count, oaipmh_key))
            