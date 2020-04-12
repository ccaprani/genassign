# -*- coding: utf-8 -*-
"""
Created on Thu Mar 26 22:45:47 2020

@author: ccapr
"""

import numpy as np


def sysK(grid):
    ''' Returns the restricted global stiffness matrix for a pre-defined
    basic grid topology
    '''
    L,I,J,E,G,M = grid
    EI = E*I
    GJ = G*J
    K = np.array([[8*EI/L + 2*GJ/L, 2*EI/L, 2*EI/L],
                  [2*EI/L, 4*EI/L, 0],
                  [2*EI/L, 0, 4*EI/L]])
    return K


def det_K(K):
    detK = np.linalg.det(K)
    return detK


def inv_K(K):
    invK = np.linalg.inv(K)
    return invK


def getF(grid):
    M = grid[5]
    return np.array([M,0,0])


def solve_D(grid):
    K = sysK(grid)
    F = getF(grid)
    return np.linalg.solve(K, F)*1e-3


def eleK(grid):
    L,I,J,E,G,M = grid
    EI = E*I
    GJ = G*J
    return np.array([[GJ/L, 0, -GJ/L, 0],
                    [0, 4*EI/L, 0, 2*EI/L],
                    [-GJ/L, 0, GJ/L, 0],
                    [0, 2*EI/L, 0, 4*EI/L]])


def d_CD(D):
    return np.array([0,D[0],0,D[2]])


def d_DC(D):
    return np.array([0,-D[2],0,-D[0]])


def d_CE(D):
    return np.array([D[0],0,0,0])


def d_FC(D):
    return np.array([0,D[2],0,D[0]])


def d_CF(D):
    return np.array([0,D[0],0,D[2]])


def d_GC(D):
    return np.array([0,0,D[0],0])


def d_CG(D):
    return np.array([D[0],0,0,0])


def eleF(k,D):
    return k.dot(D)


def m2ltx(a,style='bmatrix',suppress_small=True):
    """Returns a LaTeX bmatrix

    :a: numpy array
    :returns: LaTeX bmatrix as a string
    """
    if len(a.shape) > 2:
        raise ValueError('bmatrix can at most display two dimensions')
    
    lines = [np.array2string(s,precision=3,separator=',',
                             suppress_small=suppress_small) for s in a]
    lines = [s.replace('[', '').replace(']', '') for s in lines]
    lines = ['  ' + ' & '.join(s.split(',')) + r'\\' for s in lines]
    lines = [s.replace('.\\','\\') for s in lines]
    lines = [s.replace('. ',' ') for s in lines]
    rv = [r'\begin{' + style + '}']
    rv += lines
    rv += [r'\end{' + style + '}']
    return '\n'.join(rv)


if (__name__ == '__main__'):
    print('Executing as standalone script')
    
    # Define some inputs
    L = 4.0      # m
    I = 37.5e-6  # m4
    J = 75e-6    # m4
    E = 200      # GPa
    G = 80       # GPa
    M = -57      # Nm
    
    # Unit conversions MN/m2
    E *= 1e3
    G *= 1e3
    
    grid = [L,I,J,E,G,M]
    
    D = solve_D(grid)
    theta_C, theta_D, theta_F = D
    
    print(theta_C)
    print(theta_D)
    print(theta_F)
