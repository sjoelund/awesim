# -*- coding: utf-8 -*-
"""
This module contains tools to:
    1) access simulation parameters and results generated by dymola in 
       .mat files, or having exactly the same structure
    2) keep track of a (unlimited) amount of these simulation output files

Two classes are defined:
    1) Simulation
    2) Simdex

The main properties of those classes are discussed below.
One function is also defined: load_simdex(filename).  This function loads the
desired simdex that was previously saved with Simdex.save(filename)

class Simulation:
-----------------
    Class for doing operations one 1 single simulation file
    The simualation files are supposed to be generated by Dymola, or at 
    least have the same structure.  
    A Simulation object contains all the (useful) info that is in the .mat file.  
    Therefore, objects of the Simulation class are relatively memory intensive,
    depending on the size of the .mat file.
    
    Most important attributes are:
        - self.filename (path to the .mat file)
        - self.names (list of all variable and parameter names)
        - self.dataInfo (mapping of vars and pars to data1 and data2)
        - self.data1 (contains the values of the parameters)
        - self.data2 (contains the values of the variables (timeseries))
    
    Most important methods are:
        - get_value(name) : retreives the value(s) for name, name can be 
          a parameter or a variable
        - exist(regex) : returns all vars and pars that satisfy the regex
        
class Simdex:
-------------
    A Simdex object is an index of all the parameters and variables in several 
    .mat files.  It can be used to select a set of .mat files from a large set
    in order to analyse the results of this set of simulations.
    
    Most important attributes are:
        - self.simulations (a list of filenames of the indexed simulations)        
        - self.parameters (a list of all parameters in the set of simulations)
        - self.parametermap (numpy array mapping which simulation has 
          which parameters)        
        - self.parametervalues (numpy array containing the values of the 
          mapped parameters)
        - self.variables (a list of all variables in the set of simulations)
        - self.variablemap (numpy array mapping which simulation has 
          which variables)
        - self.filterset (dictionary tracking all executed filter options on 
          the current set) 
          
        There is no attribute containing the variable values themselves because 
        that would blow up the size of simdex.  These values are kept in the 
        original .mat files and only extracted when needed

Most important methods (* = implemented):

    * __init__(folder): create simdex based from all .mat simulation files in the 
      current folder
    - update(folderlist): update simdex with all .mat files found in a list of 
      folders. Checks if the found files are already in simulations, else they 
      are added and their parameters and ALL attributes are updated with the 
      info found in the new files
    - remove(sim_id): remove a simulation from the simdex
    * print(): gives a nice overview of the indexed simulations 
    * filter(dictionary): this method takes as input a dictionary with parameter 
      name/value pairs.   It returns a new Simdex object with those simulations
      that have exactly the same values for those parameters.  
      If a parameter is asked with '*' as value, all simulations that HAVE 
      the parameter are selected.
    * getidentical(sim_id):  this method takes as input a simulation number and 
      returns a new simdex object all simulations with identical parameter set 
      (so all variants of the model with only changed parameter values).  
    * exist(re): similar to Simulation.exist method. Give a search string as re 
      (regular expression) and you get a list of all parameters and variables 
      that satisfy the re. 
    * plot(var): directly create a plot showing the given var for each of the 
      simulations in self.
    - get_values(var or par): get an array with the values of the variable or
      parameter for each of the simulations in the simdex
    * get_parameter(par): to be merged in get_values!!
    - save(filename): saves the simdex by pickling (cPickle) to filename.  The 
      simdex can be loaded later on with the function load_simdex(filename)
      
This info AND more details can be found in the docstrings of each of these
classes, functions and methods

"""

import numpy as np
import os
import scipy.io
import re
import copy
import matplotlib.pyplot as plt
#from enthought.traits.api import *
#from enthought.traits.ui.api import *

__author__ = "Roel De Coninck"
__version__ = "0.0.1"



class Simulation:
    """
    Class for doing operations one 1 single simulation file
    The simualation files are supposed to be generated by Dymola, or at 
    least have the same structure.  
    A Simulation object contains all the (useful) info that is in the .mat file.  
    Therefore, objects of the Simulation class are relatively memory intensive,
    depending on the size of the .mat file.
    
    Most important attributes are:
        - self.filename (path to the .mat file)
        - self.names (list of all variable and parameter names)
        - self.dataInfo (mapping of vars and pars to data1 and data2)
        - self.data1 (contains the values of the parameters)
        - self.data2 (contains the values of the variables (timeseries))
    
    Most important methods are:
        - get_value(name) : retreives the value(s) for name, name can be 
          a parameter or a variable
        - exist(regex) : returns all vars and pars that satisfy the regex
    
    """
    
    def __init__(self, filename):
        ''' 
        Create a Simulation object from a .mat file
        The filename can be an absolute path, or a filename in the current work
        directory, but it must NOT have a .mat extension.
        '''
        
        # turn filename in an absolute path
        # no .mat extension needed, it is added by the scipy.io.loadmat method
        filename = os.path.abspath(filename)
        
        try:
            d = scipy.io.loadmat(filename, chars_as_strings = False) 
            # if all goes well, d is a dictionary 
            # check the fields of d to make sure we're having a dymola file
            for field in ['dataInfo','name','data_1','data_2'] :
                # here we create numpy arrays with names dataInfo, name, 
                # data_1 and data_2
                stringske = field+'=d[field].transpose()'
                exec(stringske)
        except :
            print '%s is no Dymola file.  No Simulation object created' % \
                (filename)
            raise IOError
                
        # Now we have dataInfo, data_1 and data_2 from the first Dymola file

        # data_1 contains the values of the parameters
        # data_2 contains the values of the variables (timeseries)
        # name contains parameter and variable names but it is still 'transposed'.  
        # dataInfo contains all metadata about parameters and variables 

        # For future reference, it's important to understand how the data 
        # is structured.  dataInfo has 4 columns and contains a row for
        # each row of names
        
        # Matrix with 4 columns defining the data of the signals:
        # dataInfo(i,1)= j: name i data is stored in matrix "data_j".
        # dataInfo[0,0] = 0, means that names[0] is used as abscissa
        # for ALL data matrices!  Normally, names[0]='Time'
        #
        # dataInfo(i,2)= k: name i data is stored in column abs(k) of matrix
        # data_j with sign(k) used as sign.
        #
        # dataInfo(i,3)= 0: Linear interpolation of the column data
        # = 1..4: Piecewise convex hermite spline interpolation
        # of the column data. Curve is differentiable upto
        # order 1..4. The spline is defined by a polygon.
        # It touches the polygon in the middle of every segment
        # and at the beginning and final point. Between such
        # points the spline is convex. The polygon is also the
        # convex envelope of the spline.
        #
        # dataInfo(i,4)= -1: name i is not defined outside of the defined time range
        # = 0: Keep first/last value outside of time range
        # = 1: Linear interpolation through first/last two points outside
        # of time range.
        

        names=[] 
        # names will be list with names of all parameters and variables 
               
        for i in range(name.shape[0]):
            names.append(''.join(name[i,:]).strip())        
        
                
        self.names = names
        self.dataInfo = dataInfo
        self.data_1 = data_1
        self.data_2 = data_2
        self.filename = filename

    def __str__(self):
        print self.filename
        
        return self.filename


    def get_value(self, name):
        '''
        get_value(self, name)
    
        This function returns a numpy array with the value(s) of 'name' 
        '''
        
        result=[]
        try:
            name_index = self.names.index(name)
        except (ValueError):
            print '%s could not be found in %s' % (name,self.filename)
            raise
            
        possign = self.dataInfo[name_index,1]
        pos = abs(possign)
        #pos is the row number in data_1 or data_2
        sign = np.sign(possign)
        #sign indicates the sign of the values 
        if self.dataInfo[name_index,0]==1:
            source='self.data_1'
            # it is a parameter, found in data_1
            stringske="result="+source+"[:,pos-1][0]*sign"
        elif self.dataInfo[name_index,0]==2 or self.dataInfo[name_index,0]==0:
            source='self.data_2'
            # important: by testing I found out that get_value for variables
            # gives the last value 2 times.  So I omit the last value here.
            stringske="result="+source+"[:-1,pos-1]*sign"
        else:
            raise ValueError('name not found')
        
        exec(stringske)
        return result
        
    def exist(self, regex): 
        """
        exist(regex) 
        
        regex = regular expression, not case sensitive
                
        This method searches for parameter and variable names matching the 
        regular expression in self.names.
        It returns a list with all matching names from self.names
        
        """
        
        p = re.compile(regex, re.IGNORECASE)
        matches=[]
        for i in range(0,len(self.names)):
            m = p.search(self.names[i])
            if m:
                matches.append(self.names[i])
        
        return matches

    def separate(self):
        '''
        separate()
        
        Separates variables from parameters and adds 2 lists and 1 numpy array 
        as attributes:
            - list parameters
            - list variables (timeseries)
            - numpy array parametervalues
        This method returns True if successfull
        '''
        # We create a loop over each of the elements in names, check if it is 
        # parameter or variable. We update the attributes parameters and 
        # variables, and if it is a parameter, we put the value in 
        # parametermap
    
        parameters=[]
        variables=[]
        parametervalues=[]
        # parametervalues is a list with the values of the parametes for this
        # run.  Will be converted to array and become self.parametervalues
        
        for i in range(len(self.names)):
            par_or_var = self.names[i] #string with the name of the par or var
            
            possign = self.dataInfo[i,1]
            pos = abs(possign)
            #pos is the row number in data_1 or data_2
            sign = np.sign(possign)
            #sign indicates the sign of the values 
    
            if self.dataInfo[i,0]==1:
                # par_or_var is a parameter
                parameters.append(par_or_var)
                parametervalues.append(self.data_1[0,pos-1]*sign)
    
            elif self.dataInfo[i,0]==2 or self.dataInfo[i,0]==0:
                # par_or_var is a variable (if == 0: time)
                variables.append(par_or_var)
            
            else:
                print par_or_var
                raise LookupError('Couldnt find this value in dataInfo')
            
        self.parametervalues = np.array(parametervalues) 
        self.parameters = parameters
        self.variables = variables
        
        return True



class Simdex:
    """
    A Simdex object is an index of all the parameters and variables in several 
    .mat files.  It can be used to select a set of .mat files from a large set
    in order to analyse the results of this set of simulations.
    
    Most important attributes are:
        - self.simulations (a list of filenames of the indexed simulations)        
        - self.parameters (a list of all parameters in the set of simulations)
        - self.parametermap (numpy array mapping which simulation has 
          which parameters)        
        - self.parametervalues (numpy array containing the values of the 
          mapped parameters)
        - self.variables (a list of all variables in the set of simulations)
        - self.variablemap (numpy array mapping which simulation has 
          which variables)
        - self.filterset (dictionary tracking all executed filter options on 
          the current set) 
          
        There is no attribute containing the variable values themselves because 
        that would blow up the size of simdex.  These values are kept in the 
        original .mat files and only extracted when needed

    Most important methods (* = implemented):

    * __init__(folder): create simdex based from all .mat simulation files in the 
      current folder
    - update(folderlist): update simdex with all .mat files found in a list of 
      folders. Checks if the found files are already in simulations, else they 
      are added and their parameters and ALL attributes are updated with the 
      info found in the new files
    - remove(sim_id): remove a simulation from the simdex
    * print(): gives a nice overview of the indexed simulations 
    * filter(dictionary): this method takes as input a dictionary with parameter 
      name/value pairs.   It returns a new Simdex object with those simulations
      that have exactly the same values for those parameters.  
      If a parameter is asked with '*' as value, all simulations that HAVE 
      the parameter are selected.
    * getidentical(sim_id):  this method takes as input a simulation number and 
      returns a new simdex object all simulations with identical parameter set 
      (so all variants of the model with only changed parameter values).  
    * exist(re): similar to Simulation.exist method. Give a search string as re 
      (regular expression) and you get a list of all parameters and variables 
      that satisfy the re. 
    * plot(var): directly create a plot showing the given var for each of the 
      simulations in self.
    - get_values(var or par): get an array with the values of the variable or
      parameter for each of the simulations in the simdex
    * get_parameter(par): to be merged in get_values!!
    - save(filename): saves the simdex by pickling (cPickle) to filename.  The 
      simdex can be loaded later on with the function load_simdex(filename)
      
    FEATURES:
    - all found .mat files are tested.  If they to not have the structure of
      a dymola simulation result, they are not indexed

    Important CONVENTIONS:
        - we make a distinction between parameters (one single value)
          and variables (a timeseries of values)
        - simulation 'id' is integer starting from 1, not 0
        - this means that the first column of parametermap and parametervalues
          contains only zeros
    
    Possible IMPROVEMENTS:
    - multi folder file search
    - support multiple filter (well, it's possible, but the filtersets will 
      become a bit messed up (last filterset overwrites existing filterset if 
      it has the same keys)

    """
    def __init__(self, folder=''):
        '''
        Creates a Simdex object.  
        Folders is a single folder to be sought for .mat files
        If folders = '', the current work directory is indexed.
        '''
        # First, initialise some  attributes
        self.simulations=[''] #simulations[0] is not used!
        self.filterset = dict()

        if folder=='' :
            # use current workdirectory if none is stated
            folder = os.getcwd()
        
        # here we get a list with all files in 'folder' that end with .mat
        filenames = self.__get_files(folder, '.mat')
        
        # Convert to full path filenames to avoid confusion
        full_path_filenames=[]
        for i in range(len(filenames)):
            full_path_filenames.append(os.path.join(folder,filenames[i]))
        
        # index is the pointer to the current file in full_path_filenames
        index=-1
        ########################################################################
        # Now we take the first .mat file and use this as a basis for our index
        first_file_indexed = False
        while first_file_indexed == False:
            index+=1
            try:
                # We try the .mat files one by one until we find a first Dymola file
                sim = Simulation(full_path_filenames[index])
                first_file_indexed = True
            except:
                print '%s is no Dymola file.  It is not indexed' % \
                    (full_path_filenames[index])

        # Now, check the simulation runtime and confirm with user that it is 
        # correct.  For the next simulation files, the runtime will be compared
        # to this one to decide if the file is ok or not. 
        time = sim.get_value('Time')
        
        print 'The first found simulation, %s, runs from %d s till %d s' % \
            (sim.filename,time[0],time[-1])
        timeOK = raw_input('Is this correct? y/n : ')
        print '\n'
        if timeOK=='y' or timeOK=='Y':
            self.simulationstart = time[0]
            self.simulationstop = time[-1]
        else:
            raise NotImplementedError('In that case, please remove this file \
                manually so the index can start with a correct file')
            
        # The next step is to separate parametes and variables from names and
        # initiate all attributes
        
        sim.separate()
        self.parameters = sim.parameters # a LIST
        self.variables = sim.variables  # a LIST
        self.simulations.append(sim.filename)
        self.parametermap = np.ndarray((len(self.parameters),2))
        self.parametermap[:,0] = 0
        self.parametermap[:,1] = 1
        self.parametervalues = copy.copy(self.parametermap)
        self.parametervalues[:,1] = np.array(sim.parametervalues)
        
        self.variablemap = np.ndarray((len(self.variables),2))
        self.variablemap[:,0] = 0
        self.variablemap[:,1] = 1
        
        # The first simulation file is indexed and the attributes are 
        # initialised.  
        
        ########################################################################
        # The next step is to index all remaining files
        
        index+=1
        while index < len(full_path_filenames):
            # We try to index the remaining .mat files one by one 
            try:
                sim = Simulation(full_path_filenames[index])
            
                # Now, check the simulation runtime against previously confirmed
                # start and stop times
                time = sim.get_value('Time')
                
                if self.simulationstart == time[0] and self.simulationstop == time[-1]:
                    # and the magic tric: index this new simulation in 1 line... :-)
                    self.__index_one_sim(sim)
                    print '%s indexed' % (sim.filename)
                
                    # and finally, add the filename of the nicely indexed simulation
                    # to the list of indexed simulations
                    self.simulations.append(sim.filename)
    
                else:
                    print '%s, runs from %d s till %d s, therefore, it is NOT \
                         indexed' % (sim.filename,time[0],time[-1])
            
            except :
                pass

            index+=1 

    def __str__(self):
        '''
        Prints the Simdex object as a list of the indexed simulations
        with their simID's
        '''
        print '\nsimID', 'Filename\n'
        for i in range(1,len(self.simulations)):
            print i, '   ', self.simulations[i]
        return ''
            
        
    def exist(self, regex, type = 'all'): 
        '''
        exist(regex, type='all') 
        
        regex = regular expression
        type = 'all' (default), 'par' or 'var'
        
        This function checks if a variable name exists in the index.
        In all cases, it returns a list.
        If type = 'all' this list contains 2 lists of strings: 
            the first with all parameters that satisfy the regex, 
            the second with variables that satisfy regex
        If type = 'par' or 'var' the return list only contains 
        the corresponding list.
        '''
        
        result=[]
        p = re.compile(regex, re.IGNORECASE)
        if type == 'all' or type == 'par':
            # we search for parameters
            matchespar=[]
            for i in range(0,len(self.parameters)):
                m = p.search(self.parameters[i])
                if m:
                    matchespar.append(self.parameters[i])
            result.append(matchespar)
            
        if type == 'all' or type == 'var':
            # we search for variables
            matchesvar=[]
            for i in range(0,len(self.variables)):
                m = p.search(self.variables[i])
                if m:
                    matchesvar.append(self.variables[i])
            result.append(matchesvar)

        return result
    
    
    def __get_files(self,directory, non_wildcard_pattern):
        '''
        This function returns a list of filenames as strings, satisfying the 
        nonWildCardPattern
        '''
        
        # This function was found here on 26/11/2010:
        # http://codecomments.wordpress.com/2008/07/10/find-files-in-directory-using-python/
    
        fileList = os.listdir(directory)
        return [f for f in fileList if f.find(non_wildcard_pattern) > -1]



        
    def __index_one_sim(self, simulation):
        '''
        __index_one_sim(self, simulation)
        
        This internal method adds the parameters and variables of simulation
        to the index of self.  
        simulation has to be a Simulation object
        '''
        
        # separate parameters from variables for simulation 
        simulation.separate()
        
        # newparameters and newvariables are arrays that will be updated for 
        # each parameter or variable found.  At the end, they will tell us which
        # parameters or variables are new
        newpars = np.ones(len(simulation.parameters))
        newvars = np.ones(len(simulation.variables))
        
        
        
        # PARAMETERS 
        # we run over all parameters already indexed in self.parameters
        # parmap, varmap and parvalues will map the new simulation 
        # for the already indexed parameters.  
        # So they have length = len(self.parameters)
        parmap = np.zeros((len(self.parameters),1))
        parvalues = np.zeros((len(self.parameters),1))
        
        
        for i in range(len(self.parameters)):
            # we try to find the parameter in the list of parameters from the 
            # new simulation
            partofind = self.parameters[i]
            try:
                position = simulation.parameters.index(partofind)
                # the next part is only executed if partofind is found 
                parmap[i] = 1
                parvalues[i] = simulation.parametervalues[position]
#                print i, partofind, simulation.parametervalues[position]
                # in newparameters we put a 0 if we already indexed a parameter
                newpars[position] = 0
                
            except(ValueError):
                # partofind is not found, that's fine 
                pass
        # At the end of the finished for-loop just above, we still have to 
        # add all the remaining parameters and their values
        
        newparameters = [x for (x,y) in zip(simulation.parameters,newpars) if y == 1]
        newparametervalues = [x for (x,y) in zip(simulation.parametervalues,newpars) if y == 1]
        
        if len(newparameters)>0:
            # There ARE new parameters, update the attributes
            # self.parameters
#            print 'newparameters:',newparameters
            # There ARE new parameterse, update the attributes
            self.parameters.extend(newparameters)
            
            # self.parametermap
            zeroparameters = np.zeros((len(newparameters),len(self.simulations)))
            self.parametermap = np.append(self.parametermap,zeroparameters,axis = 0)
            newparcolumn = np.append(parmap,np.ones(len(newparameters)))
            newparcolumn.resize(len(parmap)+len(newparameters),1)
            self.parametermap = np.append(self.parametermap, newparcolumn,axis = 1)
            # print 'slang', self.parametermap.shape, '\n' 
            
            # self.parametervalues
            self.parametervalues = np.append(self.parametervalues,zeroparameters,\
                axis = 0)
            newparvaluescolumn = np.append(parvalues,np.array(newparametervalues))
            newparvaluescolumn.resize(len(parvalues)+len(newparameters),1)
            self.parametervalues = np.append(self.parametervalues,\
                newparvaluescolumn,axis = 1)
        else:
            # there are no new parameters, just add the info from simulation 
            # in the current index
            self.parametermap = np.append(self.parametermap,parmap,axis = 1)
            self.parametervalues = np.hstack((self.parametervalues,parvalues))

        # VARIABLES 
        # we run over all variables already indexed in self.variables
        # varmap will map the new simulation for the already indexed variables.  
        # So they have length = len(self.variables)
        varmap = np.zeros((len(self.variables),1))
        
        for i in range(len(self.variables)):
            # we try to find the variables in the list of variables from the 
            # new simulation
            vartofind = self.variables[i]
            try:
                position = simulation.variables.index(vartofind)
                # the next part is only executed if partofind is found 
                varmap[i] = 1
                # the found variables are deleted from the list
                newvars[position] = 0
            except(ValueError):
                # vartofind is not found, that's fine 
                pass
        newvariables = [x for (x,y) in zip(simulation.variables,newvars) if y == 1]

        if len(newvariables)>0:
        
            # self.variables
            self.variables.extend(newvariables)
            
            # self.variablesmap
            zerovariables = np.zeros((len(newvariables),len(self.simulations)))
            self.variablemap = np.append(self.variablemap,zerovariables, axis = 0)
            newvarcolumn = np.append(varmap,np.ones(len(newvariables)))
            newvarcolumn.resize(len(newvarcolumn),1)
            self.variablemap = np.append(self.variablemap,newvarcolumn,axis = 1)
            
        else:
            # no new variables, just add the info from simulation 
            # in the current index
            self.variablemap = np.append(self.variablemap,varmap,axis = 1)
     
    def get_identical(self,simID):
        '''
        get_identical(simID)
        
        simID = integer
        
        Create a new Simdex object from self with only those simulations 
        that have identical parameters and variables as simID
        '''
        
        # Approache: copy self and remove the unneeded columns from 
        # parametermap, parametervalues and variablemap by slicing
        
        newsimdex = copy.copy(self)
        newsimdex.simulations=['']
        
        parmap = self.parametermap[:,simID]
        varmap = self.variablemap[:,simID]
        
        sims_to_keep = [True]
        # First value in sims_to_keep is for the dummy columns

        for i in range(1,len(self.simulations)):
            if np.all(self.parametermap[:,i]==parmap) and \
                np.all(self.variablemap[:,i]==varmap):
                # we have catched an identical simulation
                sims_to_keep.append(True)
                newsimdex.simulations.append(self.simulations[i])
            else:
                sims_to_keep.append(False)
            
        # slicing only works with an array
        s = np.array(sims_to_keep)
        newsimdex.parametermap = newsimdex.parametermap[:,s]
        newsimdex.parametervalues = newsimdex.parametervalues[:,s]
        newsimdex.variablemap = newsimdex.variablemap[:,s]
        
        # remove all empty rows and corresponding parameters/variables
        newsimdex.cleanup()
        
        return newsimdex

    def filter(self, pardic):
        '''
        filter(pardic)
        
        pardic is a dictionary of parameter:value pairs
        if a value is omitted (empty string), all simulations that have any 
        value for this parameter are fine
        
        Get all simulations that satisfy pardic (AND relation) and 
        return them as a new Simdex object
        '''
        
        # Approach: first find the parameters from pardic in self.parameters
        # and remove all rows from parametermap and parametervalues that aren't 
        # playing the game.
        # Then separate the parameters with values from the ones without
        
        # I select the rows by creating another array with the row numbers
        # and slice self.parametermap and self.parametervalues with that array
        
        rows=[]
        values=[]
        for i in pardic:
            rows.append(self.parameters.index(i))
            values.append(pardic[i])
        
        
        arows = np.array(rows)
        reduced_par_map = self.parametermap[arows]
        reduced_par_val = self.parametervalues[arows]
        
        
            
        # next step: remove all simulations that do NOT have the parameters
        # with empty strings in pardic
        
        # get row numbers of rows in reduced_par_map where the value doesn't 
        # matter
        parmaprows = np.array([x for (x,y) in zip(range(len(pardic)),\
            pardic.values()) if y==''])
        
        # if there are no parmaprows, we don't need to filter on empty strings
        if len(parmaprows)>0:
            selmap = reduced_par_map[parmaprows]
            # selmap contains rows with 0 and 1's for each of the simulations
            # (columns).  We need to get the simulation numbers (column numbers) 
            # that are FINE, meaning that the columns are unit columns
            satisfyingmap = selmap.all(axis = 0)
            # satisfying is a boolean array, true if the corresponding simulation 
            # is still in the run for selection
        else:
            # satisfyingmap has to be known.  
            # In this case a boolean array with only True values
            satisfyingmap = np.array(range(len(self.simulations)))>-1
        
        # now we need to get only the rows for which the values matter
        # and compare those values for each simulation with 'values'
        parvalrows = np.array([x for (x,y) in zip(range(len(pardic)),\
            pardic.values()) if y<>''])
        if len(parvalrows)>0:
            selval = reduced_par_val[parvalrows]
            values = values[parvalrows]
            satisfyingval = np.all(selval == values,axis = 0)
            # again a boolean array
        else:
            # satisfyingval has to be known.  
            # In this case a boolean array with only True values
            satisfyingval = np.array(range(len(self.simulations)))>-1
            
        
        # only simulations satisfying both the requirements are selected
        # first (dummy) row of self.simulations has also to be kept
        satisfying = satisfyingmap & satisfyingval
        satisfying[0] = True
        
        # we create a new simdex object, with identical properties as self
        # but containing only the simulations we have selected
        
        newsimdex = copy.copy(self)
        newsimdex.simulations=\
            [x for (x,y) in zip(self.simulations,satisfying) if y == True]
        newsimdex.parametermap = self.parametermap[:,satisfying]
        newsimdex.parametervalues = self.parametervalues[:,satisfying]
        newsimdex.variablemap = self.variablemap[:,satisfying]
            
        # we want to keep track of the parameters we have filtered on
        # this should be improved: if two identical keys occur, take the key
        # with associated value (instead of '')
        newsimdex.filterset.update(pardic)
        
        # Removing unused parameters and variables from the filtered simdex
        newsimdex.cleanup()
        
        print newsimdex


        return newsimdex
    
    def cleanup(self):
        '''
        cleanup removes unused parameters and unused variables from a simdex
        object.
        '''
        
        pars_to_keep = np.any(self.parametermap,1)
        self.parametermap = self.parametermap[pars_to_keep]
        self.parametervalues = self.parametervalues[pars_to_keep]
        self.parameters = [x for (x, y) in \
            zip(self.parameters, pars_to_keep) if y == True]
        vars_to_keep = np.any(self.variablemap,1)
        self.variables = [x for (x, y) in \
            zip(self.variables, vars_to_keep) if y == True]
        self.variablemap = self.variablemap[vars_to_keep]
        

    def get_parameter(self, parameter):
        '''
        get_parameter(parameter)
        
        parameter = string with exact parameter name
        
        This method returns a list with simID, parvalues and simulation
        filenames.  They are also printed on the screen
        '''
        
        parindex = self.parameters.index(parameter)
            # row number of the parameter to be returned
        
#        result = [range(1,len(self.simulations)),\
#            self.parametervalues[parindex,1:], self.simulations[1:]]
        
        result = self.parametervalues[parindex,:]
        # take care, first element is dummy value (zero)
        
        print '\nsimID', parameter, 'Filename\n'
        for i in range(1,len(self.simulations)):
            print i, '   ', result[i], '  ', self.simulations[i]
        
        return result

    def plot(self, variable):
        '''
        plot(variable) - variable = string with exact variable name
        
        Creates a matplotlib figure with a simple plot of the timeseries for 
        each of the simulations in self
        '''
        
        # structure of this method:
#            1. find variable name in self.variablemap
#            2. select the simulations that HAVE this variable
#            3. for each of those simulations, create a Simulation object sim
#            4. use get_value on sim to get all the values
#            5. create a plotstring to plot

            
        # 1. and 2.
        varindex = self.variables.index(variable)
        simulations = [x for (x,y) in \
            zip(self.simulations, self.variablemap[varindex,:]) if y == 1]
        simulations.insert(0,'')
        
        # 3. and 4.
        plotstring=''
        plotlegend=''
        
        for s in range(1,len(simulations)):
            sim = Simulation(simulations[s])
            if s == 1:
                #only once: get time
                time = sim.get_value('Time')
            stringske='simID_'+str(s)+"=sim.get_value('"+variable+"')"
            exec(stringske)
            plotstring+='time, simID_' + str(s) + ','
            plotlegend+="'simID_"+str(s)+ "',"
        
        plotstring = plotstring[:-1]
        plotlegend = plotlegend[:-1]
        
        fig = plt.figure()
        exec("lines = plt.plot("+plotstring+")")
        exec("leg = plt.legend(("+plotlegend+"))")
        
        return [fig,lines,leg]

    
    def get_simID(self, regex):
        '''
        get_simID(regex)
        
        regex = regular expression, not case sensitive
        
        Get a list of simulations of which the filenames match the regex
        '''
        p = re.compile(regex, re.IGNORECASE)
        matches=[]
        simids=[]
        for i in range(0,len(self.simulations)):
            m = p.search(self.simulations[i])
            if m:
                matches.append(self.simulations[i])
                simids.append(i)
        
        print 'simID', 'Filename\n'
        for i,sim in zip(simids,matches):
            print i, '   ', sim
        return simids
