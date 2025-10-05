import numpy as np


def chl_hu(Rrsblue, Rrsgreen, Rrsred):
    """
    This is the Ocean Color Index (CI) three-band reflectance difference algorithm (Hu et al. 2012). This should only be used for chlorophyll retrievals below 0.15 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. doi: 10.1029/2011jc007395

    Parameters:
        Rrsblue: numpy array of Rrs in the blue band.

        Rrsgreen: numpy array of Rrs in the green band.

        Rrsred: numpy array of Rrs in the red band.

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).

    """

    ci1 = -0.4909
    ci2 = 191.6590

    CI = Rrsgreen - (Rrsblue + (560 - 475) / (668 - 475) * (Rrsred - Rrsblue))
    ChlCI = 10 ** (ci1 + ci2 * CI)
    return ChlCI


def chl_ocx(Rrsblue, Rrsgreen):
    """
    This is the OCx algorithm which uses a fourth-order polynomial relationship (O'Reilly et al. 1998). This should be used for chlorophyll retrievals above 0.2 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. The coefficients for OC2 (OLI/Landsat 8) are used as default. doi: 10.1029/98JC02160.

    Parameters:
        Rrsblue: numpy array of Rrs in the blue band.

        Rrsgreen: numpy array of Rrs in the green band.

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).

    """

    # L8 OC2 coefficients
    a0 = 0.1977
    a1 = -1.8117
    a2 = 1.9743
    a3 = 2.5635
    a4 = -0.7218

    temp = np.log10(Rrsblue / Rrsgreen)

    log10chl = a0 + a1 * (temp) + a2 * (temp) ** 2 + a3 * (temp) ** 3 + a4 * (temp) ** 4

    ocx = np.power(10, log10chl)
    return ocx


def chl_hu_ocx(Rrsblue, Rrsgreen, Rrsred):
    """
    This is the blended NASA chlorophyll algorithm which combines Hu color index (CI) algorithm (chl_hu) and the O'Reilly band ratio OCx algortihm (chl_ocx). This specific code is grabbed from https://github.com/nasa/HyperInSPACE. Documentation can be found here https://www.earthdata.nasa.gov/apt/documents/chlor-a/v1.0#introduction.

    Parameters:
        Rrsblue: numpy array of Rrs in the blue band.

        Rrsgreen: numpy array of Rrs in the green band.

        Rrsred: numpy array of Rrs in the red band.

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).
    """

    thresh = [0.15, 0.20]
    a0 = 0.1977
    a1 = -1.8117
    a2 = 1.9743
    a3 = 2.5635
    a4 = -0.7218

    ci1 = -0.4909
    ci2 = 191.6590

    temp = np.log10(Rrsblue / Rrsgreen)

    log10chl = a0 + a1 * (temp) + a2 * (temp) ** 2 + a3 * (temp) ** 3 + a4 * (temp) ** 4

    ocx = np.power(10, log10chl)

    CI = Rrsgreen - (Rrsblue + (560 - 475) / (668 - 475) * (Rrsred - Rrsblue))

    ChlCI = 10 ** (ci1 + ci2 * CI)

    if ChlCI.any() <= thresh[0]:
        chlor_a = ChlCI
    elif ChlCI.any() > thresh[1]:
        chlor_a = ocx
    else:
        chlor_a = ocx * (ChlCI - thresh[0]) / (thresh[1] - thresh[0]) + ChlCI * (
            thresh[1] - ChlCI
        ) / (thresh[1] - thresh[0])

    return chlor_a


def chl_gitelson(Rrsred, Rrsrededge):
    """
    This algorithm estimates chlorophyll a concentrations using a 2-band algorithm with coefficients from Gitelson et al. 2007. This algorithm is recommended for coastal (Case 2) waters. doi:10.1016/j.rse.2007.01.016

    Parameters:
        Rrsred: numpy array of Rrs in the red band.

        Rrsrededge: numpy array of Rrs in the red edge band.

    Returns:
        Numpy array of derived chlorophyll (mg m^-3).
    """

    chl = 59.826 * (Rrsrededge / Rrsred) - 17.546
    return chl
