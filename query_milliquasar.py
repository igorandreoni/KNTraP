# Query The Million Quasars (Milliquas) catalogue, version 8 (Flesch, 2023)
# VII/294

from astropy.io import ascii
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.vizier import Vizier
Vizier.ROW_LIMIT = -1


def query_vizier(ra, dec, catalog, rad_deg=0.01, outfile="catalog.csv"):
    """
    Query the vizier database, write output file

    Parameters
    ----------
    ra float
        right ascension in degrees
    dec float
        declination in degrees
    catalog str
        vizier catalog id
    rad_deg float
        query radius in degrees
    outfile str
        name of the output file (CSV)

    """
    coords = SkyCoord(ra*u.deg, dec*u.deg)
    result = Vizier.query_region(coords,
                                 radius=rad_deg*u.deg, catalog=catalog)

    # Write the result
    result[0].write(outfile, format='csv', overwrite=True)


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
        outfile = f"milliquas/{t_field['objectName']}_milliquas_query_rad{radius_deg}.csv"
        # Coords
        ra, dec = t_field["ra"], t_field["dec"]
        t_milliquas = query_vizier(ra, dec, "VII/294", radius_deg,
                                   outfile=outfile)
        done.append(t_field["objectName"])

