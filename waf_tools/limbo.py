#!/usr/bin/env python
# encoding: utf-8
#| Copyright Inria May 2015
#| This project has received funding from the European Research Council (ERC) under
#| the European Union's Horizon 2020 research and innovation programme (grant
#| agreement No 637972) - see http://www.resibots.eu
#| 
#| Contributor(s):
#|   - Jean-Baptiste Mouret (jean-baptiste.mouret@inria.fr)
#|   - Antoine Cully (antoinecully@gmail.com)
#|   - Kontantinos Chatzilygeroudis (konstantinos.chatzilygeroudis@inria.fr)
#|   - Federico Allocati (fede.allocati@gmail.com)
#|   - Vaios Papaspyros (b.papaspyros@gmail.com)
#| 
#| This software is a computer library whose purpose is to optimize continuous,
#| black-box functions. It mainly implements Gaussian processes and Bayesian
#| optimization.
#| Main repository: http://github.com/resibots/limbo
#| Documentation: http://www.resibots.eu/limbo
#| 
#| This software is governed by the CeCILL-C license under French law and
#| abiding by the rules of distribution of free software.  You can  use,
#| modify and/ or redistribute the software under the terms of the CeCILL-C
#| license as circulated by CEA, CNRS and INRIA at the following URL
#| "http://www.cecill.info".
#| 
#| As a counterpart to the access to the source code and  rights to copy,
#| modify and redistribute granted by the license, users are provided only
#| with a limited warranty  and the software's author,  the holder of the
#| economic rights,  and the successive licensors  have only  limited
#| liability.
#| 
#| In this respect, the user's attention is drawn to the risks associated
#| with loading,  using,  modifying and/or developing or reproducing the
#| software by the user in light of its specific status of free software,
#| that may mean  that it is complicated to manipulate,  and  that  also
#| therefore means  that it is reserved for developers  and  experienced
#| professionals having in-depth computer knowledge. Users are therefore
#| encouraged to load and test the software's suitability as regards their
#| requirements in conditions enabling the security of their systems and/or
#| data to be ensured and,  more generally, to use and operate it in the
#| same conditions as regards security.
#| 
#| The fact that you are presently reading this means that you have had
#| knowledge of the CeCILL-C license and that you accept its terms.
#| 
import os
import stat
import subprocess
import time
import threading
import params
import license
from waflib.Tools import waf_unit_test

json_ok = True
try:
    import simplejson
except:
    json_ok = False
    print "WARNING simplejson not found some function may not work"


def options(opt):
    opt.add_option('--qsub', type='string', help='json file to submit to torque', dest='qsub')


def create_variants(bld, source, uselib_local,
                    uselib, variants, includes=". ../",
                    cxxflags='',
                    target=''):
    source_list = source.split()
    if not target:
        tmp = source_list[0].replace('.cpp', '')
    else:
        tmp = target
    for v in variants:
        deff = []
        suff = ''
        for d in v.split(' '):
            suff += d.lower() + '_'
            deff.append(d)
        bin_fname = tmp + '_' + suff[0:len(suff) - 1]
        bld.program(features='cxx',
                    source=source,
                    target=bin_fname,
                    includes=includes,
                    uselib=uselib,
                    cxxflags=cxxflags,
                    use=uselib_local,
                    defines=deff)

def summary(bld):
    lst = getattr(bld, 'utest_results', [])
    total = 0
    tfail = 0
    if lst:
        total = len(lst)
        tfail = len([x for x in lst if x[1]])
    waf_unit_test.summary(bld)
    if tfail > 0:
        bld.fatal("Build failed, because some tests failed!")

def _sub_script(tpl, conf_file):
    if 'LD_LIBRARY_PATH' in os.environ:
        ld_lib_path = os.environ['LD_LIBRARY_PATH']
    else:
        ld_lib_path = "''"
    print 'LD_LIBRARY_PATH=' + ld_lib_path
     # parse conf
    list_exps = simplejson.load(open(conf_file))
    fnames = []
    for conf in list_exps:
        exps = conf['exps']
        nb_runs = conf['nb_runs']
        res_dir = conf['res_dir']
        bin_dir = conf['bin_dir']
        wall_time = conf['wall_time']
        use_mpi = "false"
        try:
            use_mpi = conf['use_mpi']
        except:
            use_mpi = "false"
        try:
            nb_cores = conf['nb_cores']
        except:
            nb_cores = 1
        try:
            args = conf['args']
        except:
            args = ''
        email = conf['email']
        if (use_mpi == "true"):
            ppn = '1'
            mpirun = 'mpirun'
        else:
     #      nb_cores = 1;
            ppn = "8"
            mpirun = ''

        #fnames = []
        for i in range(0, nb_runs):
            for e in exps:
                directory = res_dir + "/" + e + "/exp_" + str(i)
                try:
                    os.makedirs(directory)
                except:
                    print "WARNING, dir:" + directory + " not be created"
                subprocess.call('cp ' + bin_dir + '/' + e + ' ' + directory, shell=True)
                fname = directory + "/" + e + "_" + str(i) + ".job"
                f = open(fname, "w")
                f.write(tpl
                        .replace("@exp", e)
                        .replace("@email", email)
                        .replace("@ld_lib_path", ld_lib_path)
                        .replace("@wall_time", wall_time)
                        .replace("@dir", directory)
                        .replace("@nb_cores", str(nb_cores))
                        .replace("@ppn", ppn)
                        .replace("@exec", mpirun + ' ' + directory + '/' + e + ' ' + args))
                f.close()
                os.chmod(fname, stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)
                fnames += [(fname, directory)]
    return fnames

def _sub_script_local(conf_file):
    if 'LD_LIBRARY_PATH' in os.environ:
        ld_lib_path = os.environ['LD_LIBRARY_PATH']
    else:
        ld_lib_path = "''"
    print 'LD_LIBRARY_PATH=' + ld_lib_path
     # parse conf
    list_exps = simplejson.load(open(conf_file))
    fnames = []
    for conf in list_exps:
        exps = conf['exps']
        nb_runs = conf['nb_runs']
        res_dir = conf['res_dir']
        bin_dir = conf['bin_dir']
        wall_time = conf['wall_time']
        use_mpi = "false"
        try:
            use_mpi = conf['use_mpi']
        except:
            use_mpi = "false"
        try:
            nb_cores = conf['nb_cores']
        except:
            nb_cores = 1
        try:
            args = conf['args']
        except:
            args = ''
        email = conf['email']
        if (use_mpi == "true"):
            ppn = '1'
            mpirun = 'mpirun'
        else:
     #      nb_cores = 1;
            ppn = "8"
            mpirun = ''

        #fnames = []
        for i in range(0, nb_runs):
            for e in exps:
                directory = res_dir + "/" + e + "/exp_" + str(i)
                try:
                    os.makedirs(directory)
                except:
                    print "WARNING, dir:" + directory + " not be created"
                subprocess.call('cp ' + bin_dir + '/' + e + ' ' + '"' + directory + '"', shell=True)
                fname = e
                fnames += [(fname, directory)]
    return fnames,args

def run_local_one(directory, s):
    std_out = open(directory+"/stdout.txt", "w")
    std_err = open(directory+"/stderr.txt", "w")
    retcode = subprocess.call(s, shell=True, env=None, stdout=std_out, stderr=std_err)

def run_local(conf_file, serial = True):
    fnames,arguments = _sub_script_local(conf_file)
    threads = []
    for (fname, directory) in fnames:
        s = "cd " + '"' + directory + '"' + " && " + "./" + fname + ' ' + arguments
        print "Executing " + s
        if not serial:
            t = threading.Thread(target=run_local_one, args=(directory,s,))
            threads.append(t)
        else:
            run_local_one(directory,s)

    if not serial:
        for i in range(len(threads)):
            threads[i].start()
        for i in range(len(threads)):
            threads[i].join()

def qsub(conf_file):
    tpl = """#!/bin/sh
#? nom du job affiche
#PBS -N @exp
#PBS -o stdout
#PBS -b stderr
#PBS -M @email
# maximum execution time
#PBS -l walltime=@wall_time
# mail parameters
#PBS -m abe
# number of nodes
#PBS -l nodes=@nb_cores:ppn=@ppn
#PBS -l pmem=5200mb -l mem=5200mb
export LD_LIBRARY_PATH=@ld_lib_path
exec @exec
"""
    fnames = _sub_script(tpl, conf_file)
    for (fname, directory) in fnames:
        s = "qsub -d " + directory + " " + fname
        print "executing:" + s
        retcode = subprocess.call(s, shell=True, env=None)
        print "qsub returned:" + str(retcode)


def oar(conf_file):
    tpl = """#!/bin/bash
#OAR -l /nodes=1/core=@nb_cores,walltime=@wall_time
#OAR -n @exp
#OAR -O stdout.%jobid%.log
#OAR -E stderr.%jobid%.log
export LD_LIBRARY_PATH=@ld_lib_path
exec @exec
"""
    print 'WARNING [oar]: MPI not supported yet'
    fnames = _sub_script(tpl, conf_file)
    for (fname, directory) in fnames:
        s = "oarsub -d " + directory + " -S " + fname
        print "executing:" + s
        retcode = subprocess.call(s, shell=True, env=None)
        print "oarsub returned:" + str(retcode)

def output_params(folder):
    files = [each for each in os.listdir(folder) if each.endswith('.cpp')]
    output = ''
    for file in files:
        output += 'FILE: ' + folder + '/' + file + '\n\n'
        output += params.get_output(folder + '/' + file)
        output += '=========================================\n'

    text_file = open("params_"+folder[4:]+".txt", "w")
    text_file.write(output)
    text_file.close()

def insert_license(): license.insert()
