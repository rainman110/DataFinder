# pylint: disable=C0103,R0912
# $Filename$ 
# $Authors$
# Last Changed: $Date$ $Committer$ $Revision-Id$
# Copyright (c) 2003-2011, German Aerospace Center (DLR)
# All rights reserved.
#
#
#Redistribution and use in source and binary forms, with or without
#
#modification, are permitted provided that the following conditions are
#met:
#
# * Redistributions of source code must retain the above copyright 
#   notice, this list of conditions and the following disclaimer. 
#
# * Redistributions in binary form must reproduce the above copyright 
#   notice, this list of conditions and the following disclaimer in the 
#   documentation and/or other materials provided with the 
#   distribution. 
#
# * Neither the name of the German Aerospace Center nor the names of
#   its contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
#LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR 
#A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT 
#OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
#SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT 
#LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, 
#DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY 
#THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.  


"""
This module provides the target for running the unit tests.
"""


import os
import sys

from distutils.cmd import Command

from datafinder_distutils.configuration import BuildConfiguration


__version__ = "$Revision-Id:$" 


_UNITTEST_OUTPUT_DIR = "build/unittest"
_NOSE_DEFAULT_SCRIPT = "nosetests-script.py"

class test(Command):
    """ Runs all unit tests. """

    description = "Runs all unit tests."
    user_options = [("nosecommand=",
                     None,
                     "Path and name of the nose command."),
                     ("outputformat=",
                      None,
                      "Specifies the output format of the test results." \
                      + "Formats: xml, standard out. Default: standard out."),
                      ("coveragecommand=",
                      None,
                      "Optionally, path and name of the coverage command."),
                      ("coverageoutputformat=",
                      None,
                      "Specifies the output format of the coverage report." \
                      + "Formats: xml, html. Default: html")]


    def __init__(self, distribution):
        """ Constructor. """

        self.verbose = None
        self.nosecommand = None
        self.outputformat = None
        self.coveragecommand = None
        self.coverageoutputformat = None
        self.__buildConfiguration = BuildConfiguration()
        Command.__init__(self, distribution)

    def initialize_options(self):
        """ Definition of command options. """

        self.nosecommand = _NOSE_DEFAULT_SCRIPT
        self.outputformat = None
        self.coveragecommand = "coverage"
        self.coverageoutputformat = None
        self.verbose = False

    def finalize_options(self):
        """ Set final values of options. """

        self.verbose = self.distribution.verbose
        if sys.platform == "win32" and self.nosecommand == _NOSE_DEFAULT_SCRIPT:
            self.nosecommand = os.path.join(os.path.normpath(sys.exec_prefix), "Scripts", self.nosecommand)
            
    def run(self):
        """ Perform command actions. """

        # Run sub commands
        for commandName in self.get_sub_commands():
            self.run_command(commandName)
            
        # Run tests
        testdir = os.path.join("test", "unittest")
        if self.outputformat == "xml":
            noseOptions = "--with-xunit --xunit-file=" + _UNITTEST_OUTPUT_DIR + "/xunit.xml %s" 
        else:
            noseOptions = "--verbosity=2 -d %s"
        
        noseCommand = self.nosecommand + " " + noseOptions % (testdir)
        if not self.coverageoutputformat is None:
            noseCommand = self.coveragecommand \
                        + " run --branch --source=src/datafinder,test/unittest/datafinder_test " \
                        + noseCommand
        else:
            noseCommand = "%s %s" % (sys.executable, noseCommand) 
                        
        if self.verbose:
            print(noseCommand)
        os.system(noseCommand)

        if not self.coverageoutputformat is None:
            if self.coverageoutputformat == "html":
                coverageCommand = "%s %s --omit=*gen* -d %s" % (self.coveragecommand, 
                                                   self.coverageoutputformat, 
                                                   _UNITTEST_OUTPUT_DIR)
            else: # xml
                coverageCommand = "%s %s --omit=*gen*" % (self.coveragecommand, self.coverageoutputformat)
            
            if self.verbose:
                print(coverageCommand)
            os.system(coverageCommand)
            
    def _runGenTarget(self):
        """ Checks whether the gen build target is available. Within a source
        distribution this may not the case. """

        return os.path.exists(os.path.join(self.__buildConfiguration.distutilTargetPackagePath, 
                                           "gen.py"))
    
    
    sub_commands = [("_prepare", None), ("gen", _runGenTarget)]
