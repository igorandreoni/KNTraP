#!/usr/bin/env python

""" 
KNTraP_download_ccdbyccd.py -- Download DECam Community pipeline ccd-by-ccd stacked data uploaded to the archive where each file is a separate CCD (as opposed to all CCDs being a multiple extensions of the same file like instcal noao archive files). Currently will download all filters available satisfying RA/DEC/caldat/prod_types criteria entered, and get instrument=decam, telescope=ct4m, obs_type=object, proc_type=stacked.

Note that   
pipesrc_dir      = os.getenv('PIPE_SRC')
pipe_instru      = os.getenv('PIPE_INSTRUMENT')
pipe_projec      = os.getenv('PIPENAME')
Given the field name, each CCD's central position is found in the pipesrc_dir/config/pipe_instru/pipe_projec/pipe_projec.fieldcenters file. 

Usage: 
    KNTraP_download_ccdbyccd.py [-h] [-v] [--debug] [--do_not_download] [--credentials STRING] [--search_radius FLOAT] [--file_string STRING] [--prod_types STRING] <caldat> <pointing_name> 

Arguments:
    caldat (string)
        is the local calendar date of the telescope, at the start of PM observing. Please only enter 1 caldat.
    pointing_name (string)
        e.g. S82sub8
    
Options:
    -h, --help                      Show this screen
    -v, --verbose                   Print extra info to screen. [default: False]
    --debug                         Print input docopt arguments [default: False]
    --do_not_download               Just print what it'll download but not download it [default: False]
    --credentials STRING            Format: USERNAME,PW
    --search_radius FLOAT           In degrees, default is 36" [default: 0.01]
    --file_string STRING            E.g. v1, kfttest [default: kfttest]
    --prod_types STRING             Choose from: image, image1, wtmap, dqmask, expmap [default: image1,wtmap,dqmask]

Examples:
    KNTraP_download_ccdbyccd.py 2021-06-05 S82sub8 --do_not_download -v --credentials XXX,XXX
"""
import docopt
import pandas as pd
import numpy as np
import requests
import json
import astropy.io.ascii as ascii
import os
import copy
import time
import datetime

# Time Counter function

def tic():
    tic.start = time.perf_counter()

def toc():
    elapsed_seconds = time.perf_counter() - tic.start
    return elapsed_seconds # fractional

# Organisational functions

def file_string_in_x(x,file_string):
    if file_string in x:
        in_x = True
    else:
        in_x = False
    return in_x

def makedirs_(out_path):
    out_dir = '/'.join(out_path.split('/')[0:-1])
    os.makedirs(out_dir, exist_ok=True)
    return None

# Calculation functions

def  get_radec_maxmin(RAcentre,DECcentre,search_radius_deg, debug=False):

    dec_min = DECcentre - search_radius_deg
    dec_max = DECcentre + search_radius_deg
    if dec_min<-90.0: dec_min=-90.0
    if dec_max>90.0: dec_max=90.0
    if dec_min==-90.0 or dec_max==90.0:
        ra_min = 0
        ra_max = 360.0
    else:
        costerm = min(np.cos(dec_min*np.pi/180.0),np.cos(dec_max*np.pi/180.0))
        ra_min = RAcentre-search_radius_deg*1./costerm
        ra_max = RAcentre+search_radius_deg*1./costerm
        if ra_min<0: ra_min+=360.0
        if ra_max>360.0: ra_max-=360.0

    if debug:
        print('**** DEBUG: ',dec_min, dec_max)
        print('**** DEBUG: ',ra_min, ra_max)

    return ra_min,ra_max,dec_min,dec_max


# How to match CCD in KNTraP.fieldcenters to CCD code in saved raw data file name. 
ccd_code_dic = {
1:'S29', '1':'S29',
2:'S30', '2':'S30',
3:'S31', '3':'S31',
4:'S25', '4':'S25',
5:'S26', '5':'S26',
6:'S27', '6':'S27',
7:'S28', '7':'S28',
8:'S20', '8':'S20',
9:'S21', '9':'S21',
10:'S22', '10':'S22',
11:'S23', '11':'S23',
12:'S24', '12':'S24',
13:'S14', '13':'S14',
14:'S15', '14':'S15',
15:'S16', '15':'S16',
16:'S17', '16':'S17',
17:'S18', '17':'S18',
18:'S19', '18':'S19',
19:'S8', '19':'S8',
20:'S9', '20':'S9',
21:'S10', '21':'S10',
22:'S11', '22':'S11',
23:'S12', '23':'S12',
24:'S13', '24':'S13',
25:'S1', '25':'S1',
26:'S2', '26':'S2',
27:'S3', '27':'S3',
28:'S4', '28':'S4',
29:'S5', '29':'S5',
30:'S6', '30':'S6',
31:'S7', '31':'S7',
32:'N1', '32':'N1',
33:'N2', '33':'N2',
34:'N3', '34':'N3',
35:'N4', '35':'N4',
36:'N5', '36':'N5',
37:'N6', '37':'N6',
38:'N7', '38':'N7',
39:'N8', '39':'N8',
40:'N9', '40':'N9',
41:'N10', '41':'N10',
42:'N11', '42':'N11',
43:'N12', '43':'N12',
44:'N13', '44':'N13',
45:'N14', '45':'N14',
46:'N15', '46':'N15',
47:'N16', '47':'N16',
48:'N17', '48':'N17',
49:'N18', '49':'N18',
50:'N19', '50':'N19',
51:'N20', '51':'N20',
52:'N21', '52':'N21',
53:'N22', '53':'N22',
54:'N23', '54':'N23',
55:'N24', '55':'N24',
56:'N25', '56':'N25',
57:'N26', '57':'N26',
58:'N27', '58':'N27',
59:'N28', '59':'N28',
60:'N29', '60':'N29',
61:'N30', '61':'N30',
62:'N31', '62':'N31'
}

# Json needed to make a request to NOAO archive. 
jj_base = {    
        "outfields" : [
            "md5sum",
            "archive_filename",
            "original_filename",
            "proc_type",
            "prod_type",
            "proposal",
            "ra_center",
            "dec_center",
            "caldat",
            "url",
            "filesize",
            "ifilter",
            "exposure",
            "dateobs_min",
            "dateobs_max" 
            ],
        "search" : [ ["instrument", 'decam'],
                     ["telescope", 'ct4m'],
                     ["obs_type", 'object'],
                     ["proc_type","stacked"],
                   ]
    }
##############################################################
####################### Main Function ########################
##############################################################


def KNTraP_download_ccdbyccd(caldat,pointing_name,
                                username=None, pw=None,
                                search_radius_deg=0.01,
                                file_string='kfttest',
                                prod_types=['image1','wtmap','dqmask'],
                                verbose=False,debugmode=False,
                                do_not_download=False):

    # Start the timer
    if verbose or debugmode:
        print(f'VERBOSE: Started on: {str(datetime.datetime.now())}')
    tic() # Start timing the run of this notebook

    # Get environment variables for photpipe set up
    pipesrc_dir      = os.getenv('PIPE_SRC')
    pipe_instru      = os.getenv('PIPE_INSTRUMENT')
    pipe_projec      = os.getenv('PIPENAME')
    pipedata_dir     = os.getenv('PIPE_DATA')
    f_field_centers  = f'{pipesrc_dir}/config/{pipe_instru}/{pipe_projec}/{pipe_projec}.fieldcenters'
    raw_dir          = f'{pipedata_dir}/raw/'

    # NOAO server Settings
    natroot = 'https://astroarchive.noirlab.edu'
    assert natroot == 'https://astroarchive.noirlab.edu', 'Notebook does NOT point to PRODUCTION'
    adsurl = f'{natroot}/api/adv_search'
    apiurl = f'{adsurl}/fasearch/?limit=200000'

    # Print some information if debug:
    if debugmode:
        print(f"**** DEBUG: Using server on {natroot}")
        print(f"**** DEBUG: adsurl = {adsurl}")
        print(f'**** DEBUG: Using API url: {apiurl}')

    # Read in fieldcenters file (need it for each ccd's RA and DEC centers)
    d_field_centers                = ascii.read(f_field_centers)
    df_field_centers               = pd.DataFrame(d_field_centers.as_array())
    df_field_centers_selectedfield = df_field_centers[df_field_centers['field']==pointing_name]

    # Just do a subset of CCDs if in debugmode so can get through it faster for tests.
    if debugmode:
        ccds_to_go_through = np.arange(2)
        print('**** DEBUG: Just going through 2 CCDs worth of data')
    else:
        ccds_to_go_through = np.arange(len(df_field_centers_selectedfield))

    # =======================================================================
    # For each CCD, query and download (if not told not to) what's specified.  
    # =======================================================================
    for ii in ccds_to_go_through:

        # Get CCD RA and DEC centre limits
        ccd               = df_field_centers_selectedfield.iloc[ii]['ampl']
        print(f'\n############### Working on CCD {ccd} ###############\n')
        RAcentre          = df_field_centers_selectedfield.iloc[ii]['RAdeg'] #226.54167   
        DECcentre         = df_field_centers_selectedfield.iloc[ii]['DECdeg'] #9.54861
        ra_min,ra_max,dec_min,dec_max = get_radec_maxmin(RAcentre,DECcentre,search_radius_deg,debug=debugmode)

        # Perform query of NOAO archive
        if ra_min>ra_max:
            raise RuntimeError('This needs to be fixed!!')
            # Need to perform two searches to account for overlap
            
        else:
            jj=copy.deepcopy(jj_base)
            jj['search'].append(['ra_center',ra_min,ra_max])
            jj['search'].append(['dec_center',dec_min,dec_max])
            jj['search'].append(["caldat",caldat,caldat])
            if debugmode:
                print('**** DEBUG: Search json: ')
                print(jj)
            ads_df = pd.DataFrame(requests.post(apiurl,json=jj).json()[1:])

        # Print some query output stats
        print('Retrieved: ',len(ads_df))
        ads_df_with_string = ads_df[ [file_string_in_x(x,file_string) for x in ads_df['archive_filename']] ]
        print(f'Retrieved and filtered through only those with {file_string} in archive_filename: ',len(ads_df_with_string))
        print('')

        # ==============================================================
        # Print info on and download if specified each file for this CCD. 
        for index, row in ads_df_with_string.iterrows():
            if row['prod_type'] in prod_types:
                if verbose or debugmode:
                    print('\nVERBOSE: ======================')
                    print('VERBOSE: WORKING ON A NEW FILE:',row['archive_filename'].split('/')[-1])
                    print('VERBOSE: ======================')
                    for k in row.keys():
                        print(f'VERBOSE: {k:18s}: {row[k]}')
                    print('')
                else:
                    print(f'For {row["archive_filename"]} -->')
                dlink           = row['url']
                caldat_filename = row['caldat'].replace('-','')
                band            = row['ifilter'].split(' ')[0]
                ccd_code        = ccd_code_dic[ccd]
                prod_type_code  = row['archive_filename'].split('/')[-1].split('_')[3]
                out_file_name   = f'{pointing_name}.{caldat_filename}_{prod_type_code}_{band}_{file_string}_{ccd_code}.fits.fz'
                out_path        = f'{raw_dir}/{pointing_name}/{ccd}/{out_file_name}'
                makedirs_(out_path)

                print('Will save as: ',out_path)

                # Do the actual downloading
                if not do_not_download:
                    print('... Downloading...:')
                    headers = dict()
                    fileID = row['md5sum']
                    fileurl = f'{natroot}/api/retrieve/{fileID}'
                    tokurl = f'{natroot}/api/get_token/'
                    auth = dict(email=username, password=pw)
                    r = requests.post(tokurl, json=auth)
                    if r.status_code == 200:
                        token = r.json()
                        headers = dict(Authorization=token)
                        r2 = requests.get(fileurl,headers=headers)
                        if r2.status_code == 200:
                            print(f'Read file with size={len(r2.content):,} bytes')
                            open(out_path, 'wb').write(r2.content) # write temp file
                            print(f'Saved: {out_path}')
                        else:
                            msg = f'Error getting file ({requests.status_codes._codes[r2.status_code][0]}). {r2.json()["message"]}'
                            raise Exception(msg)
                    else:
                        raise Exception(f"Could got get authorization: {token['detail']}")
    
    # Finish timer
    elapsed = toc()
    print(f'Elapsed seconds={elapsed}')
    print(f'Completed on: {str(datetime.datetime.now())}')
    return None


############################################################################
####################### BODY OF PROGRAM STARTS HERE ########################
############################################################################

if __name__ == "__main__":

    # Read in input arguments
    arguments           = docopt.docopt(__doc__)
    # Code running mode arguments
    debugmode           = arguments['--debug']
    if debugmode:
        print(arguments)
    verbose             = arguments['--verbose']
    do_not_download     = arguments['--do_not_download']
    # Required arguments
    caldat              = arguments['<caldat>']
    pointing_name       = arguments['<pointing_name>']
    # Optional arguments 
    credentials         = arguments['--credentials']
    if credentials:
        username,pw     = credentials.split(',')
    search_radius_deg   = float(arguments['--search_radius'])
    file_string         = arguments['--file_string']
    prod_types          = arguments['--prod_types']
    prod_types          = prod_types.split(',')


    _ = KNTraP_download_ccdbyccd(caldat,pointing_name,
                                username=username,pw=pw,
                                search_radius_deg=search_radius_deg,
                                file_string=file_string,
                                prod_types=prod_types,
                                verbose=verbose,debugmode=debugmode,
                                do_not_download=do_not_download)
