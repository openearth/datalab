# -*- coding: utf-8 -*-
"""
Created on Tue Mar 04 15:07:09 2014

@author: hendrik_gt

python pointworker -c pg_connectionslocal.txt -u D:\projecten\openearth\3TU\datamanagement\test

"""

import os
import sys
import glob
import argparse
import numpy as np
from StringIO import StringIO
from collections import Counter

import pandas
import psycopg2


def perform_sql(sql,credentials):
    conn = psycopg2.connect("dbname={dbname} host={host} user={user} password={password}".format(**credentials))
    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
        print "query type, # rows affected) -- "+cur.statusmessage
    except psycopg2.ProgrammingError,e:
        print e.pgerror
        sys.exit
    except Exception,e:
        print e.message
        sys.exit
    finally:
        cur.close()
        conn.close()

# function to read textfile with keys and values. The keys have to be uname, pwd, host and dbname for 
# respectively username, password, hostname of the server and a database name. For the databasename None is the 
# default value. The credential file can be used for every database on a particular server (with respect to the rights assigned)
# if dbase is not specified as parameter to the function the dbase specified in the credenital file will be used
def get_credentials(credentialfile,dbase=None):
    fdbp = open(credentialfile,'rb')
    credentials = {}
    if dbase != None:
        credentials['dbname'] = dbase
    for i in fdbp:
        item = i.split('=')
        if str.strip(item[0]) == 'dbname':
            if dbase == None:
                credentials['dbname'] = str.strip(item[1])
        if str.strip(item[0]) == 'uname':
            credentials['user'] = str.strip(item[1])
        if str.strip(item[0]) == 'pwd':
            credentials['password'] = str.strip(item[1])
        if str.strip(item[0]) == 'host':
            credentials['host'] = str.strip(item[1])
    print 'credentials set for database ',credentials['dbname'],'on host',credentials['host']
    print 'for user',credentials['user']
    return credentials    


def executesqlfetch(strsql,credentials):
    conn = psycopg2.connect("dbname={dbname} host={host} user={user} password={password}".format(**credentials))
    cur = conn.cursor()
    try:
        cur.execute(strsql)
        p = cur.fetchall()
        return p
    except psycopg2.ProgrammingError,e:
        print 'test',e.pgerror
        return False
    except Exception,e:
        print e.message
        return False
    finally:
        cur.close()
        conn.close()

def create_table(schema,table,dctfields,credentials):
    strsql = """create table {s}.{t} (""".format(s=schema,t=table)
    for i in range(len(dctfields.keys())):
        k = dctfields.keys()[i]
        if i == len(dctfields.keys())-1:
            strsql = ''.join([strsql,k.lower(),' ',dctfields[k],')'])
        else:
            strsql = ''.join([strsql,k.lower(),' ',dctfields[k],','])
    
    print strsql
    perform_sql(strsql,credentials)
    return        

def flushCopyBuffer(bufferFile,atable,credentials,cols):
    conn = psycopg2.connect("dbname={dbname} host={host} user={user} password={password}".format(**credentials))
    cur = conn.cursor()
    bufferFile.seek(0)   # Little detail where lures the deamon...
    cur.copy_from(bufferFile, atable, sep=',',columns=cols)
    cur.connection.commit()
    bufferFile.close()
    bufferFile = StringIO()
    return bufferFile

def getpgtypefromdf(atype):
    if str(atype) == 'object':
        return 'text'
    elif str(atype) == 'datetime64[ns]':
        return 'timestamp'
    elif str(atype) == 'int64':
        return 'integer'
    elif str(atype) == 'float64':
        return 'double precision'
    else:
        return 'text'

""" --------------------------------------------------------------------------------
function checkdomainvalues creates for every object field (i.e. character field) 
which should be in the datamodel of the database whether the values in that specific field
are present in the domaintable.

For instance, the domaintable sampledevice has the following entries:
- Emmer
- Boomkor

If a specific user loads a file with Emmer, Boomkor and Emmertje there will be an 
error on Emmertje, which will not be found.

The disadvantage of this method is that fieldnames in the textfile should exactly match the
colomnames in the database.

The first part creates a dictionary of unique values for each column in the dataframe
The second part validates the contents of this dictionary with the domain tables following the names
of the keys in the dictionary. If a value of a key is not available in the table then a message is given
"""
def checkdomainvalues(df,credentials):
    uvs = {}
    dftypes = df.dtypes
    for c,t in enumerate(dftypes.index):
        if dftypes[t] == object:
            if t != 'date':
                cnt = Counter()
                for word in df[t]:
                    cnt[word] += 1
                uvs[t] = cnt.keys() 
            
    
    #build strsql from the values for each key (which is table name of domain)
    # these values will be used in the where clausule
    dictvals = {}
    for k in uvs.keys():
        values = ''
        asize = np.size(uvs[k])
        cnt = 0
        for i in uvs[k]:
            if asize > 1:
                cnt+=1
                if cnt == asize:
                    values = ''.join([values,"""'""",(i).lower(),"""'"""])
                else:
                    values = ''.join([values,"""'""",(i).lower(),"""',"""])
            else:
                values = ''.join([values,"""'""",(i).lower(),"""'"""])
        
        strsql = """SELECT lower({domain}description),id{domain} FROM {domain} WHERE lower({domain}description) in ({value})""".format(domain=k,value=values)
        r = executesqlfetch(strsql,credentials)
        if r != False:
            dictvals[k] = r
        else:
            sys.exit
        
        for l in range(len(uvs[k])):
            dv = uvs[k][l]
            if (dv.lower() in [dictvals[k][x][0] for x in range(len(dictvals[k]))]) == False:
                print 'given',dv,'not known in table', k
                return False
    return dictvals


def createtablefromdf(df,table):
    columns = []
    strsql = """create table {t}("""
    dftypes = df.dtypes
    for c,t in enumerate(dftypes.index):
        columns.append(str(t))
        if c != (df.shape[1]-1):
            strsql = ''.join([strsql,str(t),' ',getpgtypefromdf(dftypes[t]),','])
        else:
            strsql = ''.join([strsql,str(t),' ',getpgtypefromdf(dftypes[t]),')'])        
    strsql = strsql.format(t=table)
    perform_sql(strsql,credentials)


def checkdfdate(df):
    have_datetime64 = False
    dtypes = df.dtypes
    for i, k in enumerate(dtypes.index):
        dt = dtypes[k]
        #print 'dtype', dt, dt.itemsize
        if str(dt.type)=="<type 'numpy.datetime64'>":
            have_datetime64 = True
    
    if have_datetime64:
        print 'correcting datetime64 to datetime'
        d2=df.copy()
        for i, k in enumerate(dtypes.index):
            dt = dtypes[k]
            if str(dt.type)=="<type 'numpy.datetime64'>":
                d2[k] = [ v.to_pydatetime() for v in d2[k] ]
                #convert datetime64 to datetime
                #ddt= [v.to_pydatetime() for v in dd] #convert datetime64 to datetime
        return d2
    else:
        return df

def df2pglocations(df,credentials,tbl):
    """
    first copy entire table to the dump table using filebuffer

    This part does:
    - create row location_point
    - alter dump table to add columns: thegeom, thegeography, idlocation
    - set thegeom, thegeography...
    - relate idlocation in dump to location_point
    """
    ioResult = StringIO()
    columns = df.columns
    df.to_csv(ioResult,index=False,header=False,cols=columns)
    print 'loading data to database'
    flushCopyBuffer(ioResult,tbl,credentials,columns)
    #
    # - create row location_point
    #
    """create sql to insert locations into location table"""
    strSql = """insert into location_point (orig_srid, origx, origy,thegeometry)
                select orig_srid, origx, origy, 
                ST_Transform(ST_SetSRID(ST_MakePoint(origx, origy),orig_srid), 4326) from {t}""".format(t=tbl)
    perform_sql(strSql,credentials)
    #
    # - alter dump table to add columns: thegeom, thegeography, idlocation
    # - set thegeom, thegeography...
    #
    strSql = """alter table {t} add column thegeography geography""".format(t=tbl)
    perform_sql(strSql,credentials)
    
    strSql = """update {t} set thegeography = 
    ST_GeographyFromText(st_asEWKT(ST_Transform(ST_SetSRID(ST_MakePoint(origx, origy),orig_srid), 4326)))""".format(t=tbl)
    perform_sql(strSql,credentials)

    strSql = """alter table {t} add column thegeom geometry(POINT,4326)""".format(t=tbl)
    perform_sql(strSql,credentials)
    
    strSql = """update {t} set thegeom = 
    ST_Transform(ST_SetSRID(ST_MakePoint(origx, origy),orig_srid), 4326)""".format(t=tbl)
    perform_sql(strSql,credentials)
    
    #create field idlocation and update that field
    strSql = """alter table {t} add column idlocation integer""".format(t=tbl)
    perform_sql(strSql,credentials)

    #
    # - relate idlocation in dump to location_point
    #
    strSql = """update {t} d
        set idlocation = loc.idlocation from
        (
         SELECT l.idlocation as idlocation, ST_GeographyFromText(st_asEWKT(l.thegeometry)) as thegeography 
            FROM {t} As d, location_point As l   
         WHERE st_dwithin(d.thegeography,ST_GeographyFromText(st_asEWKT(l.thegeometry)),0.5)
         ORDER BY ST_Distance(d.thegeom,l.thegeometry)
        ) as loc
        where st_dwithin(d.thegeography,loc.thegeography,0.5)""".format(t=tbl)
    perform_sql(strSql,credentials)

def df2pgobservations(df,credentials,tbl):
    """create sql to insert values in observation table"""
    strsql = """
    insert into observation (idlocation, value, date, idquality,idsamplemethod,idsampledevice,idproperty,idparameter,idunit,idcompartment,idmeasurementmethod,idprocessingjob)
        select idlocation, value, date, idquality,idsamplemethod,idsampledevice,idproperty,idparameter,idunit, idcompartment,idmeasurementmethod,1
        from {t} d
        join parameter pa on lower(pa.parameterdescription) = lower(d.parameter)
        join quality q on lower(q.qualitydescription) = lower(d.quality)
        join samplemethod s on lower(s.samplemethoddescription) = lower(d.samplemethod)
        join sampledevice sd on lower(sd.sampledevicedescription) = lower(d.sampledevice)
        join measurementmethod mm on lower(mm.measurementmethoddescription) = lower(d.measurementmethod)
        join property p on lower(p.propertydescription) = lower(d.property)
        join compartment c on lower(c.compartmentdescription) = lower(d.compartment)
        join unit u on u.unitdescription = d.unit
        """.format(t=tbl)
    perform_sql(strsql,credentials)

#cf = r'D:\projecten\openearth\3TU\datamanagement\test\pg_connectionprops_local.txt'
#dirin = r'D:\projecten\openearth\3TU\datamanagement\test'
#chunksize = 1000




if __name__ == '__main__':
    adescr= """
            This procedure loads csv files in the Sand Engine PostgreSQL/PostGIS database.
            2 inputs are required:
                - directory with csv files
                - file with credentials
            
            The csv files have to meet the following requirements:
                - header consisting of at least orig_srid, origx, origy,value, date, quality,samplemethod,sampledevice,property,parameter,unit
                - fields names should be consistent with tablenames with domainvalues
                - contents of the fields after date should be in text and should meet the Aquo standards (visit http://www.aquo.nl/Aquo/schemas/ for information on the contents)
            
            File with credentials should have the following parameters:
                - uname = 
                - pwd   = 
                - host  = 
                - dbname = 
            
            Each csv will be validated using the contents of the columns quality, samplemethod,sampledevice,property, parameter and unit
            against the domaintables with the same name. Validation will be done on the column <>description (e.g. unitdescription)
            a user will get a warning and the procedure stops if validation results in a value for the mentioned column which does not exists in the domaintable under consideration.
            """
    parser = argparse.ArgumentParser(description=adescr)
    parser.add_argument('--path', '-u', default=None, type=str, help='path to collection of csv files')
    parser.add_argument('--cf','-c', default=None, type=str, help='file with credentials for access to the databaase')
    parser.add_argument('--chs','-chs', default=1000, type=int, help='chunksize to cut the input files into pieces for performance reasons (default = 1000 records)')
    args = parser.parse_args()

        
    cf = args.cf  #r'D:\projecten\openearth\3TU\datamanagement\test\pg_connectionprops_local.txt'
    dirin = args.path #r'D:\projecten\openearth\3TU\datamanagement\test'
    chunksize = args.chs
    print 'credentials file', cf
    print 'path with csv',dirin
    print 'chunksize',chunksize
    credentials = get_credentials(cf)

    """first create schema"""
    strsql = """create schema dump"""
    perform_sql(strsql,credentials)
    
    
    for pf in glob.glob(os.path.join(dirin,'*.csv')):
        print 'reading',pf
        df = pandas.read_csv(pf,parse_dates=['date'])
        
        """check if one of the columns is datetime64, if so, it will be corrected to datetime
           deal with datetime64 to_csv() bug"""
        df = checkdfdate(df)
        
        
        """create table"""
        tbl = ''.join(['dump','.',os.path.basename(pf).split('.')[0]])
        createtablefromdf(df,tbl)
        
        """checking domain values, this is done using the column names of the csv that exactly match
        the table names. Then the content of the tables is matched with the unique value of the matching fields in the csv"""
        dictvals = checkdomainvalues(df,credentials)
        if  dictvals == False:
            print "please append the domaintable listed or correct the data"
            sys.exit
        else:
            """ add locations to the table and perform insert query
                this can take a while because of the fact that there is a trigger on the locations_point table"""
            
            """check the size of the datafram, for now the chunksize = 1000"""
            if df.shape[0] > chunksize:
                ni = int(round(df.shape[0]/chunksize))
                i = 0
                for n in range(1,ni):
                    if n==0:
                        print 'chunksize loading of data, step',1,'of',ni
                    else:
                        print 'chunksize loading of data, step',n,'of',ni
                        
                    if n != ni:
                        dfc = df.iloc[i:n*chunksize]
                    else:
                        dfc = df.iloc[i:]
                    i = n*chunksize
                    df2pglocations(dfc,credentials,tbl)
                    df2pgobservations(dfc,credentials,tbl)
                    strsql = """delete from {t}""".format(t=tbl)
                    perform_sql(strsql,credentials)
            else:
                df2pglocations(df,credentials,tbl)
                df2pgobservations(df,credentials,tbl)
                strsql = """delete from {t}""".format(t=tbl)
                perform_sql(strsql,credentials)
            
            """clean up"""
            strsql = """drop table {t}""".format(t=tbl)
            perform_sql(strsql,credentials)
    
    """drop schema"""
    strsql = """drop schema dump"""
    perform_sql(strsql,credentials)
