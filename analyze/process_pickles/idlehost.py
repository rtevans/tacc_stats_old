#!/usr/bin/env python
import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import numpy
import scipy, scipy.stats
import argparse
import re
import multiprocessing
import functools
import tspl, tspl_utils, lariat_utils

def do_isidle(file,thresh,idleness):
  idleness[file]=isidle(file,thresh)

def isidle(file,thresh):
  k1=['amd64_core','amd64_sock','cpu']
  k2=['SSE_FLOPS', 'DRAM',      'user']
  try:
    ts=tspl.TSPLSum(file,k1,k2)
  except tspl.TSPLException as e:
    return

  if not tspl_utils.checkjob(ts,3600,[x+1 for x in range(16)]): # 1 hour
    return
  elif ts.numhosts < 2: # At least 2 hosts
    print ts.j.id + ': 1 host'
    return


  mr=[]
  for i in range(len(k1)):
    maxrate=numpy.zeros(len(ts.t)-1)
    for h in ts.j.hosts.keys():
      rate=numpy.divide(numpy.diff(ts.data[i][h]),numpy.diff(ts.t))
      maxrate=numpy.maximum(rate,maxrate)
    mr.append(maxrate)

  sums=[]
  for i in range(len(k1)):
    for h in ts.j.hosts.keys():
      rate=numpy.divide(numpy.diff(ts.data[i][h]),numpy.diff(ts.t))
      sums.append(numpy.sum(numpy.divide(mr[i]-rate,mr[i]))/(len(ts.t)-1))

  if max(sums) > thresh:
    return True
  else:
    return False

def main():
  parser = argparse.ArgumentParser(description='Find jobs with a single highly'
                                   ' idle host')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-t', metavar='threshold',
                      help='Treshold idleness',
                      nargs=1, default=[0.001])
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()
  
  thresh=1.-n.t[0]
  filelist=tspl_utils.getfilelist(n.filearg)

  pool     = multiprocessing.Pool(processes=n.p[0])
  m        = multiprocessing.Manager()
  idleness = m.dict()
  
  partial_isidle=functools.partial(do_isidle,thresh=thresh,idleness=idleness)

  if len(filelist) != 0:
    pool.map(partial_isidle,filelist)
    pool.close()
    pool.join()


  print '----------- Idle Jobs -----------'
  for i in idleness.keys():
    if idleness[i]:
      print i.split('/')[-1]

  
if __name__ == '__main__':
  main()
  
