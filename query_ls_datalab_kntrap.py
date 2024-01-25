# Author: Igor Andreoni
# Query Legacy Survey via datalab
# To install dl: pip install --ignore-installed --no-cache-dir astro-datalab

import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.io import ascii

from dl import queryClient as qc
import dl


def query_coords_ls(ra, dec, radius_deg,
                    catalog='ls_dr10',
                    outfile="datalab_query.csv"):
    '''Query datalab'''

    #Crossmatch with tractor table
    query = qc.query(sql=f"SELECT objid, ra, dec, type, \
mag_g, flux_g, flux_ivar_g, \
mag_r, flux_r, flux_ivar_r, \
mag_i, flux_i, flux_ivar_i, \
mag_z, flux_z, flux_ivar_z \
from {catalog}.tractor \
where 't' = Q3C_RADIAL_QUERY(ra, dec, {ra}, {dec}, {radius_deg})")
# Not present in dr10
# z_phot_median, z_phot_std \

    # Write the result in CSV format
    with open(outfile, "w") as f:
        f.write(query)


if __name__ == "__main__":
    # Read the target file
    filename = "kntrap-target-list.csv" 
    t = ascii.read(filename, format='csv')
    # Search radius
    radius_deg = 1.2
    # Iterate over the fields
    done = []
    for t_field in t:
        if t_field["objectName"] in done:
            continue
        print(f"Querying {t_field['objectName']}")
        # Output filename (CSV)
        outfile = f"ls/{t_field['objectName']}_ls_query_rad{radius_deg}.csv"
        # Coords
        ra, dec = t_field["ra"], t_field["dec"]
        query_coords_ls(ra, dec, radius_deg, catalog='ls_dr10',
                        outfile=outfile)
        done.append(t_field["objectName"])
