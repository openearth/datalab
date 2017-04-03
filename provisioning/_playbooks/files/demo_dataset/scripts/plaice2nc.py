# -*- coding: utf-8 -*-
"""
Created on Fri Aug 09 11:14:14 2013

@author: hendrik_gt


TODO implement the CF-SDN metadata, check
check www.seadatanet.org/Standards-Software/Metadata-formats

Descr. converts txt raster files with the growth of plaice to netCDF4-classic files

"""

import os
import sys
import subprocess
from datetime import datetime, timedelta

import glob
import netCDF4
import pandas


def showhelp():
    msg = """
    This routine is created for the FP7 VECTORS projects (http://marine-vectors.eu) in order to convert model results to netCDF's that can be stored on 
    an OPeNDAP server for visualisation purposes (check http://maps.marine-vectors.eu for the demo version). 
    
    The routine works with ASCII raster like files without a header (very uncommon), therefore the main also consists of the header of the ASCII (nrows, ncols, llx,lly,nodatavalue)
    
    To Be Done: read dimensions (nrows, ncols, llx,lly,nodatavalue) from a textfile as input.
    
    dependencies:
    - glob
    - netCDF4
    - pandas
    - gdal_translate (should be available in the path and comes with QGIS and other OSGeo packages)    
    
    usage:
    python plaice2nc.py <inputdirectory> <wildcard (file extension)> <outputdirectory>
    """
    print msg

# function that converts from geotiff to nc and removes geotif
def gdalasc2nc(af, metatagname):
    print 'in gdalasc2nc',af,metatagname
    anc = af.replace('.asc', '.nc')
    nodata = str(-9999.0)
    args = ['gdal_translate', '-mo', "META-TAG={}".format(metatagname),
            '-a_nodata',nodata,af, '-of', 'netCDF', anc]
    
    try:
        subprocess.call(args)
        os.unlink(af)
        return anc
    except BaseException as err:
        print err.args
        print 'Please check:'
        print '  if gdal_translate is in path environment'
        print 'Status of:'
        print '  ',af,'exists =',os.path.isfile(af)
        print 'Complete list of arguments'
        print subprocess.list2cmdline(args)
        return False
        sys.exit() 
    

# determiune min and max values of the netCDF
def gdal_ncrange(anc,subset):
    min = netCDF4.Dataset(anc).variables[subset][:].min()
    max = netCDF4.Dataset(anc).variables[subset][:].max()
    return min,max

# next function sets some predefined global variables, not created by the
# gdal_translate routine. The globals are used by the GMDB, so if nc's
# are not used by the GMDB, this function can be neglected.
# coordinate system is set to wgs84 (EPSG4326).
# an opened nc (dataset) is required
def setglobals(dataset,daynum):
    setattr(dataset, 'institution', 'IMARES')
    setattr(dataset, 'coordinate_system', 'wgs84, EPSG4326')
    setattr(dataset, 'reference', 'http://www.wageningenur.nl/en/Expertise-Services/Research-Institutes/imares.htm')
    setattr(dataset, 'naming_authority', 'IMARES')
    setattr(dataset, 'keywords_vocabulary', 'http://www.eionet.europa.eu/gemet')
    setattr(dataset, 'cdm_data_type', 'grid')
    setattr(dataset, 'creator_name', 'Lorna Teal')
    setattr(dataset, 'creator_url', 'http://www.wageningenur.nl/en/Expertise-Services/Research-Institutes/imares.htm')
    setattr(dataset, 'creator_email', 'lorna.teal@wur.nl')
    setattr(dataset, 'project', 'Vectors - DEB')
    setattr(dataset, 'processing_level', 'final')
    setattr(dataset, 'acknowledgment', 'none')
    setattr(dataset, 'standard_name_vocabulary', 'http://cf-pcmdi.llnl.gov/documents/cf-standard-names/')
    setattr(dataset, 'license', 'geossUserRegistration')
    setattr(dataset, 'time_coverage_start', (datetime(1989,1,1)+(int(daynum)-1)*timedelta(hours=24)).isoformat())
    setattr(dataset, 'time_coverage_end', (datetime(1989,1,1)+(int(daynum))*timedelta(hours=24)).isoformat())
    setattr(dataset, 'time_coverage_duration', '1')
    setattr(dataset, 'time_coverage_resolution', '1')
    setattr(dataset, 'id', 'no UUID or OID available')
    setattr(dataset, 'history', 'Data that was created and used in Teal et al. 2012 GCB to show suitable habitats based on potential for growth. Original cellsize 10x10 kilometers.')
    setattr(dataset, 'comment', 'dataset created for model comparison work')
    setattr(dataset,'date_created','none')
    setattr(dataset,'geospatial_lat_min',str(dataset.variables['lat'][0]))
    setattr(dataset,'geospatial_lat_max',str(dataset.variables['lat'][len(dataset.variables['lat']) - 1]))
    setattr(dataset,'geospatial_lat_units','degrees')
    setattr(dataset,'geospatial_lon_min',str(dataset.variables['lon'][0]))
    setattr(dataset,'geospatial_lon_max',str(dataset.variables['lon'][len(dataset.variables['lon']) - 1]))
    setattr(dataset,'geospatial_lon_units','degrees')
    setattr(dataset,'geospatial_vertical_min','inapplicable')
    setattr(dataset,'geospatial_vertical_max','inapplicable')
    setattr(dataset,'geospatial_vertical_resolution','inapplicable')
    setattr(dataset,'geospatial_vertical_units','inapplicable')

def createascii(outputfile,llx,lly,dx,dy,ncols,nrows,df):
    ascii = open(outputfile,'w')
    ascii.write('ncols        '+str(ncols)+'\r\n')
    ascii.write('nrows        '+str(nrows)+'\r\n')
    ascii.write('XLLCORNER    '+str(llx)+'\r\n')
    ascii.write('YLLCORNER    '+str(lly)+'\r\n')
    ascii.write('DX           '+str(dx)+'\r\n')
    ascii.write('DY           '+str(dy)+'\r\n')
    ascii.write('NODATA_VALUE '+str(-9999.)+'\r\n')
    try:
        for i in range(len(df)-1,0,-1):
            astring = ''
            for k in range(0,len(df.keys())-1):    
                astring = astring + ' ' + str(df[df.keys()[k]][i])
            astring = astring.replace('nan','-9999.0')
            ascii.write(astring+'\r\n')
    except IOError:
        print IOError.message
    finally:    
        ascii.close()

def get_arrays(url,values="Band1"):
    dataset = netCDF4.Dataset(url)
    vals = dataset.variables[values][:]
    lon = dataset.variables["lon"][:]
    lat = dataset.variables["lat"][:]
    dataset.close()
    return {'lat': lat, 'lon': lon, 'vals':vals}

# open the nc to append metadata
def alternc(anc,daynum):
    dsm = netCDF4.Dataset(anc,mode='r+')
    adct = get_arrays(anc)
    dy = len(adct['lat'])
    dx = len(adct['lon'])
    dsm.variables['lon'].units = 'degrees east'
    dsm.variables['lon'].longname = 'longitude in degrees'
    dsm.variables['lon'].standard_name = 'longitude'
    
    dsm.variables['lat'].units = 'degrees north'
    dsm.variables['lat'].longname = 'latitude in degrees'
    dsm.variables['lat'].standard_name = 'latitude'
    
    # TODO implement CF_SDN parameters and link to WoRMS vocab
    dsm.variables['Band1'].long_name = 'Growth of plaice'
    dsm.variables['Band1'].standard_name = 'growth_plaice'
    dsm.variables['Band1'].resolution = '{y} by {x} degrees (North - East)'.format(y=str(dy),x=str(dx))
    dsm.variables['Band1'].geospatial_lat_resolution = '{y} degrees North'.format(y=str(dy))
    dsm.variables['Band1'].geospatial_lon_resolution = '{x} degrees East'.format(x=str(dx))
    dsm.variables['Band1'].nodataval = '-9999.'
    dsm.variables['Band1'].keywords = 'ecophysiology'
    dsm.variables['Band1'].date_created = 'april 2013'
    dsm.variables['Band1'].summary = 'Data that was created and used in Teal et al. 2012 GCB to show suitable habitats based on potential for growth within the Vectors - DEB project'
    setglobals(dsm,daynum)
    dsm.close()


# next function creates the nc including the first dataset derived from the previously created
# netCDF. It copies the structured with the difference that it will create a multidimensional nc.   
def createfnc(anc,adct):
    dsm = netCDF4.Dataset(anc,mode='r')
    dsm.createDimension('lon',len(adct['lon']))
    dsm.createDimension('lat',len(adct['lat']))
    dsm.createDimension('times',365)
        
    lon = dsm.createVariable('lon','d',dimensions=('lon'))
    lon[:] = adct['lon']
    lon.units = 'degrees east'
    lon.longname = 'longitude in degrees'
    lon.standard_name = 'longitude'
    
    lat = dsm.createVariable('lat','d',dimensions=('lat'))
    lat[:] = adct['lat']
    lat.units = 'degrees north'
    lat.longname = 'latitude in degrees'
    lat.standard_name = 'latitude'
    
    times = dsm.createVariable('time','f8',dimensions=('times'))
    times.units = 'hours since 0001-01-01 00:00:00.0'
    times.calendar = 'gregorian'
    
    dates = [datetime(1989,1,1)+n*timedelta(hours=24) for n in range(365)]
    times[:] = netCDF4.date2num(dates,units=times.units,calendar=times.calendar)
    
    data = dsm.createVariable('plaice_large','d',dimensions=('times','lat','lon'))
    data[0,:,:] = adct['vals']
    data.long_name = 'Growth of plaice'
    data.standard_name = 'growth_plaice'
    data.resolution = '{y} by {x} degrees (North - East)'.format(y=str(dy),x=str(dx))
    data.geospatial_lat_resolution = '{y} degrees North'.format(y=str(dy))
    data.geospatial_lon_resolution = '{x} degrees East'.format(x=str(dx))
    data.nodataval = '-9999.'
    data.keywords = 'ecophysiology'
    data.date_created = 'zie docje'
    data.summary = 'Data that was created and used in Teal et al. 2012 GCB to show suitable habitats based on potential for growth within the Vectors - DEB project'
    return dsm


if __name__ == '__main__':
    """
    The arguments:
    1. input directory
    2. wildcard
    3. output directory
    """
    #if len(sys.argv) <= 1:
    showhelp()
    #sys.exit()
    dirin =	'/home/worker/usecasetest/'
    dirin =	os.path.join(os.path.dirname(__file__), '../../', 'raw')
    #dirout = '/home/worker/results/'
    dirout = os.path.join(os.path.dirname(__file__), '../', '..', 'results')
    wc = '*.txt'

    if not os.path.isdir(dirout):
        print 'dirout 3 is not a path or the path is not correct'
        print dirout
        sys.exit()
    else:
        print 'output directory is {dir}'.format(dir=dirout)

    print ' ---'
    print glob.glob(os.path.join(dirin,wc))
    for pf in glob.glob(os.path.join(dirin,wc)):
        df = pandas.DataFrame.from_csv(pf,sep='\s*')
        dft = df.T
        
        llx = -7
        lly = 48.3
        dx = 0.166666666667
        dy = 0.099259259
        ncols = dft.shape[1]-1
        nrows = dft.shape[0]-1
        
        of = os.path.join(dirout,os.path.basename(pf).replace('.txt','.asc'))
        createascii(of,llx,lly,dx,dy,ncols,nrows,dft)
        
        basenm = os.path.basename(pf).replace('.txt','')
        anc = gdalasc2nc(of, basenm)
        if anc:
            daynum = basenm.split('_day_')[1]
            alternc(anc,daynum)
        else:    
            print 'error occurred while processing {af}'.format(af=anc)
