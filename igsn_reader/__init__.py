'''
Created on 3 May 2019

@author: alex
'''
from ._igsn_reader import settings, IGSNReader
from ._igsn_reader_sqlite import IGSNReader_SQLite
from ._igsn_reader_postgres import IGSNReader_postgres

def get_IGSNReader(db_engine=None, *args, **kwargs):  
    '''
    Class factory function to return subclass of DatasetMetadataCache for specified db_engine
    ''' 
    db_engine = db_engine or settings['database_engine']
    
    if db_engine == 'SQLite':
        return IGSNReader_SQLite(*args, **kwargs)
    elif db_engine == 'Postgres':
        return IGSNReader_postgres(*args, **kwargs)
    else:
        raise BaseException('Unhandled db_engine "{}"'.format(db_engine))