#!/usr/bin/env python
# coding: utf-8

import pvlib
import pandas as pd 
import numpy as np      
import matplotlib.pyplot as plt
import timeit
from solcast_frames.latlng import LatLng
from solcast_frames.radiationframehandler import RadiationFrameHandler
from solcast_frames.powerframehandler import PowerFrameHandler
from datetime import datetime, timedelta
import solcast as sc
import requests
from dateutil import tz
from timezonefinder import TimezoneFinder
import pytz
from pytz import timezone


def extractPVGIShourly(lats,longs,startyear,endyear):
    '''
    
    :params lats: list/ df column of latitudes of interest
    :params longs: list/ df column of longitudes of interest
    :params startyear: starting year of interest
    :params endyear: end year of interest
    
    :returns: list of json files of PVGIS historical output for time period and coordinate of interest
    '''
    results = list()
    for i in range(0, len(lats)):
        res = requests.get('https://re.jrc.ec.europa.eu/api/v5_2/seriescalc?lat='+f'{lats[i]}'+'&lon='+f'{longs[i]}'+'&startyear='+f'{startyear}'+'&endyear='+f'{endyear}'+'&outputformat=json&components=1') 
        if res.status_code == 200:
            results.append(res.json())
        else:
            print('Boo!' + f'{res.status_code}')
    return results

def offset(lat,long):
    """
    returns a location's time zone offset from UTC in hours.
    """
    tf=TimezoneFinder()
    utc = pytz.utc
    today = datetime.now()
    tz_target = timezone(tf.certain_timezone_at(lat=lat, lng=long))
    # ATTENTION: tz_target could be None! handle error case
    today_target = tz_target.localize(today)
    today_utc = utc.localize(today)
    return (today_utc - today_target).total_seconds() / (60*60)


def pvgisjson_2_df(output, offset):
    """
    A function for turning a pvgis api outputted file into a pandas dataframe
    
    :params output: outputted PVGIS json file requested from PVGIS API
    :params offset: output from offset(lat,long) function, number of hours offset from UTC to desired time zone
    
    :returns: pandas dataframe with outputs from PVGIS with adjusted time data to desired timezone
    """
    
    r = output
    data = pd.DataFrame(r['outputs']['hourly'])
    data ['Date'] = pd.to_datetime(data['time'], format = "%Y%m%d:%H%M")
    data['Date']+= pd.Timedelta(hours=offset)
    data['Date_dt']=pd.to_datetime(data['Date'])
    data.drop(axis = 1, labels = 'time', inplace = True )
    return data


def interp_hour_to_10mins(df, column: str, index, mins: int):
    """
    A function to interpolate between hour increments of a dataframe 
    
    :params df: Dataframe of interest, must be the dataframe where column is located
    :params column: String name of column in dataframe
    :params index: identifying the relevant row index for interpolation
    :params mins: number from 1-5 representing (+10/20/30/40/50 mins to starting time of PVGIS data)
    
    :return: interpolated value of column variable for time of interest
    """
    
    interp = np.linspace(df[column][index], df[column][index+1], num = 7)
    return interp[mins]

def data_collation(year,month,day,hour,minute,dataset):
    '''
    
    :params year: year of interest must be  within the period of PVGIS data  supplied 
    :params month: month of interest must be  within the period of PVGIS data  supplied 
    :params hour: hour of interest must be  within the period of PVGIS data  supplied 
    :params minute: minute of interest, must refer to the starting time 
    :params dataset: set of PVGIS data converted to dataframes  
    
    :returns : dataframe with required time-based solar data   
    '''
    tenmin_ghis=pd.DataFrame(columns = ['Gb(i)','Gd(i)','Gr(i)','H_sun', 'T2m','WS10m'])
    date = datetime(year,month,day,hour,minute)
    tempdf=pd.DataFrame() 
    converted = pd.DataFrame()
    converted['Date']= pd.to_datetime(dataset[0]['Date'], format = '%Y-%m-%d %H:%M:%S')
    #create timestamps 
    times = []
    for i in range(0, len(dataset)):
        times.append((date + timedelta(minutes= 10*i)))
    timespd=pd.DataFrame(times, columns=['Times'])
    for i in range(0, len(timespd['Times'])):
        if timespd['Times'][i] in converted['Date'].unique():
            index = dataset[i].index[converted['Date'] == timespd['Times'][i]]
            triggertime = timespd['Times'][i]
            tempdf['Gb(i)'] = dataset[i]['Gb(i)'][index].values #W/m2 - Direct in-plane irradiance
            tempdf['Gd(i)'] = dataset[i]['Gd(i)'][index].values #W/m2 - Diffuse in-plane irradiance
            tempdf['Gr(i)'] = dataset[i]['Gr(i)'][index].values #W/m2 - reflected in plane irradiance
            tempdf['H_sun'] = dataset[i]['H_sun'][index].values #degrees - Sun height
            tempdf['T2m'] = dataset[i]['T2m'][index].values # degrees Celsius - Air temperature
            tempdf['WS10m'] = dataset[i]['WS10m'][index].values
            tenmin_ghis = pd.concat([tenmin_ghis, tempdf])
            tempdf.iloc[0:0]
        else:
            n_tendiff = int(((timespd['Times'][i] - triggertime).total_seconds())/600)
            #return n_tendiff
            tempdf['Gb(i)'] = interp_hour_to_10mins(dataset[i], 'Gb(i)', index, n_tendiff)
            tempdf['Gd(i)'] = interp_hour_to_10mins(dataset[i], 'Gd(i)', index, n_tendiff)
            tempdf['Gr(i)'] = interp_hour_to_10mins(dataset[i], 'Gr(i)', index, n_tendiff)
            tempdf['H_sun'] = interp_hour_to_10mins(dataset[i], 'H_sun', index, n_tendiff)
            tempdf['T2m'] = interp_hour_to_10mins(dataset[i], 'T2m', index, n_tendiff)
            tempdf['WS10m'] = interp_hour_to_10mins(dataset[i], 'WS10m', index, n_tendiff)
            tenmin_ghis = pd.concat([tenmin_ghis, tempdf])
            tempdf.iloc[0:0]
    tenmin_ghis.insert(0, 'Time', times)
    tenmin_ghis.reset_index(inplace=True)
    return tenmin_ghis

def data_collation_monthly(year,month,day,hour,minute,dataset):
    '''
    
    :params year: year of interest must be  within the period of PVGIS data  supplied 
    :params month: month of interest must be  within the period of PVGIS data  supplied 
    :params hour: hour of interest must be  within the period of PVGIS data  supplied 
    :params minute: Must refer to the starting time 
    :params dataset: set of PVGIS data converted to dataframes  
    
    :returns : dataframe with required time-based solar data   
    '''
    tenmin_ghis=pd.DataFrame(columns = ['Gb(i)','Gd(i)','Gr(i)','H_sun', 'T2m','WS10m'])
    date = datetime(year,month,day,hour,minute)
    tempdf=pd.DataFrame() 
    start = datetime(year,month,day,hour,minute)
    start_str = start.strftime('%Y-%m-%d %X')
    #create timestamps 
    triggertime = []
    times = []
    if len(dataset) > 6:
        y = 0
        for y in range(0,6):
            triggertime.append(start_str)
        for z in range(6, len(dataset)):
            triggertime.append(((start + timedelta(hours=1)).strftime('%Y-%m-%d %X')))
        for w in range(12, len(dataset)):
            triggertime.append(((start + timedelta(hours=2)).strftime('%Y-%m-%d %X')))
    else: 
        for y in range(0,len(dataset)+1):
            triggertime.append(start_str)
    
    for i in range(0, len(dataset)):
        times.append((date + timedelta(minutes= 10*i)))
    timespd=pd.DataFrame(times, columns=['Times'])
    index = dataset[0].index[dataset[0]['Date'] == triggertime[0]]
    tempdf['Gb(i)'] = dataset[0]['Gb(i)'][index].values #W/m2 - Direct in-plane irradiance
    tempdf['Gd(i)'] = dataset[0]['Gd(i)'][index].values #W/m2 - Diffuse in-plane irradiance
    tempdf['Gr(i)'] = dataset[0]['Gr(i)'][index].values #W/m2 - reflected in plane irradiance
    tempdf['H_sun'] = dataset[0]['H_sun'][index].values #degrees - Sun height
    tempdf['T2m'] = dataset[0]['T2m'][index].values # degrees Celsius - Air temperature
    tempdf['WS10m'] = dataset[0]['WS10m'][index].values
    tenmin_ghis = pd.concat([tenmin_ghis, tempdf])
    tempdf.iloc[0:0]
    #print(tenmin_ghis)
    pattern = [1, 2, 3, 4, 5,6,0]
    desired_length = len(dataset)
    repeated_list = pattern * ((desired_length // len(pattern)) + 1)
    #print(repeated_list)
    for i in range(1, len(timespd['Times'])):
           # n_tendiff = int(((timespd['Times'][i] - pd.Timestamp(triggertime[i])).total_seconds())/600)
            n_tendiff = repeated_list[i-1]
            tempdf['Gb(i)'] = interp_hour_to_10mins(dataset[i], 'Gb(i)', index, n_tendiff)
            tempdf['Gd(i)'] = interp_hour_to_10mins(dataset[i], 'Gd(i)', index, n_tendiff)
            tempdf['Gr(i)'] = interp_hour_to_10mins(dataset[i], 'Gr(i)', index, n_tendiff)
            tempdf['H_sun'] = interp_hour_to_10mins(dataset[i], 'H_sun', index, n_tendiff)
            tempdf['T2m'] = interp_hour_to_10mins(dataset[i], 'T2m', index, n_tendiff)
            tempdf['WS10m'] = interp_hour_to_10mins(dataset[i], 'WS10m', index, n_tendiff)
            tenmin_ghis = pd.concat([tenmin_ghis, tempdf])
            tempdf.iloc[0:0]
    tenmin_ghis.insert(0, 'Time', times)
    tenmin_ghis.reset_index(inplace=True)
    return tenmin_ghis


def solar_data_processing(df):
    '''
    :params df: dataframe containing PVGIS processed outputs (from above function)
    
    :returns: cell temperature, aoi, IAM, total irradiance
    '''
    df['aoi'] = 90 - df['H_sun']
    df['IAM'] = [pvlib.iam.martin_ruiz(df['aoi'][i]) for i in range(0,len(df))]
    #Calculate total irradiance incident on panels
    # Used equation GHI = DNI * IAM * cos(H_sun) + DHI 
    df['TII'] = df['Gb(i)']*df['IAM']*np.cos(np.deg2rad(df['H_sun']))+df['Gd(i)']
    #calculate cell temperatures
    df['T_cell'] = pvlib.temperature.faiman(df['TII'], df['T2m'], wind_speed = df['WS10m'])
    df.drop(axis = 1, labels = 'index', inplace = True )
    return df


def calculate_power_energy(df, n_panels, P_stc, gamma_p):
    '''
    :params df: output from solar_data_processing, must contain columns T_cell, and TII
    :params n_panels: number of solar panels being modelled
    :params P_stc: power output of modelled solar panels under standard test conditions, usually reported by the manufacturer
    :params gamma_p: temperature coefficient of power of modelled solar panels provided by manufacturer
    
    :returns: dataframe with added columns power and energy, with each row representing hte energy produced in each 10 min intervale, add together to get total energy yielded
    '''
    df['Power'] = n_panels*P_stc*(1+gamma_p*(df['T_cell']-25))*(df['TII']/1000)
    df['Energy']=df['Power']*10/60
    return df



