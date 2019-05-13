import os
import logging
import re
import requests
from lxml import etree
from time import sleep
import psycopg2

from ._igsn_reader import settings, IGSNReader

DEBUG_MAX_SAMPLES = 0 # Number of samples to store before finishing while in debug mode
REPORT_INCREMENT = 1000 # Number of records to insert before reporting progress
MAX_RETRIES = 2 # Maximum number of times to retry request
RETRY_SLEEP = 2 # Seconds to sleep before retrying request

logger = logging.getLogger(__name__)

if settings['debug']:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.debug('Logger {} set to level {}'.format(logger.name, logger.level))

class IGSNReader_postgres(IGSNReader):
    
    DEFAULT_POSTGRES_AUTOCOMMIT = True
    
    def __init__(self,
                 postgres_host=None, 
                 postgres_port=None, 
                 postgres_dbname=None, 
                 postgres_user=None, 
                 postgres_password=None, 
                 autocommit=None, 
                 debug=False
                 ):
        '''
        IGSNReader_postgres class Constructor
        '''
        super(IGSNReader_postgres, self).__init__()

        self.postgres_host = postgres_host or settings.get('postgres_server') or 'localhost'
        self.postgres_port = int(postgres_port or settings.get('postgres_port') or 5432)
        self.postgres_dbname = postgres_dbname or settings.get('postgres_dbname') or 'IGSN_OAIPMH'
        self.postgres_user = postgres_user or settings.get('postgres_user') or 'db_user'
        self.postgres_password = postgres_password or settings.get('postgres_password') or 'db_password'
        self.autocommit = autocommit if autocommit is not None else IGSNReader_postgres.DEFAULT_POSTGRES_AUTOCOMMIT
        
        self.db_connection = psycopg2.connect(host=self.postgres_host, 
                                              port=self.postgres_port, 
                                              dbname=self.postgres_dbname, 
                                              user=self.postgres_user, 
                                              password=self.postgres_password)
        
        if self.autocommit:
            self.db_connection.autocommit = True
            self.db_connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        else:
            self.db_connection.autocommit = False
            self.db_connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            
        logger.debug('Connected to database {}:{}/{} as {}'.format(self.postgres_host, 
                                                                       self.postgres_port, 
                                                                       self.postgres_dbname,
                                                                       self.postgres_user))    
        
        cursor = self.db_connection.cursor()       
        for key, value in settings['oai_pmh_endpoints'].items():
            try:
                cursor.execute("""insert into OAIPMH (OAIPMH_KEY, OAIPMH_URL)
                    values (%(key)s, %(value)s);
                    """, {'key': key, 
                          'value': value})
                self.db_connection.commit()
                if cursor.rowcount:
                    logger.info('"{}" inserted into OAIPMH table for key {}'.format(value, key))
            except Exception as e:
                logger.debug('{}'.format(e))    
                                
    def read_igsns(self, oaipmh_source=None, resumption_token=None):
        '''
        Function to read IGSNS into database
        '''
        insert_sql = '''insert into sample (
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
    %(oaipmh_id)s,
    %(identifier)s,
    %(datestamp)s,
    %(alt_identifiers)s,
    %(title)s,
    %(subject)s,
    %(description)s,
    %(type)s,
    %(format)s,
    %(coverage)s,
    %(creator)s,
    %(publisher)s,
    %(rights)s
    );
'''                        

        cursor = self.db_connection.cursor()
        cursor.execute('select OAIPMH_ID, OAIPMH_KEY, OAIPMH_URL from OAIPMH')
        
        for oaipmh_id, oaipmh_key, oaipmh_url in cursor.fetchall():
            # Skip any sources not in specified source list
            if oaipmh_source and oaipmh_key != oaipmh_source:
                continue
            
            logger.debug('Querying records for {}'.format(oaipmh_key))
            
            http_params = {'verb': 'ListRecords',
                           'metadataPrefix': 'oai_dc',
                           'resumptionToken': resumption_token}
        
            sample_count = 0            
            while not sample_count or resumption_token:
                logger.debug('resumption_token = {}'.format(resumption_token))
                if resumption_token:
                    http_params = {'verb': 'ListRecords',
                                   'resumptionToken': resumption_token}
                    
                retries = 0
                while retries < MAX_RETRIES:
                    retries += 1
                    try:
                        logger.debug('oaipmh_url = {}, headers={}, params={}, data={}, timeout={}'.format(oaipmh_url, None, http_params, None, settings['timeout']))
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
                        
                    except Exception as e:
                        logger.warning('Attribute read failed: {}'.format(e))
                        continue
                            
                    logger.debug('Inserting record for {}'.format(insert_params['identifier']))
                    insert_cursor = self.db_connection.cursor()
                    logger.debug(insert_params)
                    try:
                        insert_cursor.execute(insert_sql, insert_params)
                        self.db_connection.commit()
                    except Exception as e:
                        logger.debug(e)
                        
                    sample_count += 1
                    
                    if sample_count % REPORT_INCREMENT == 0:
                        logger.info('{} samples updated'.format(sample_count))
                    
                    if settings['debug'] and DEBUG_MAX_SAMPLES > 0 and sample_count == DEBUG_MAX_SAMPLES:
                        break
                
                if settings['debug'] and DEBUG_MAX_SAMPLES > 0 and sample_count >= DEBUG_MAX_SAMPLES:
                    logger.debug('Debug limit reached')
                    break

                        
            logger.info('{} samples updated for {}'.format(sample_count, oaipmh_key))
                        