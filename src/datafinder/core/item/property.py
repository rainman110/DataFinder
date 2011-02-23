# $Filename$ 
# $Authors$
# Last Changed: $Date$ $Committer$ $Revision-Id$
#
# Copyright (c) 2003-2011, German Aerospace Center (DLR)
# All rights reserved.
#
#
#Redistribution and use in source and binary forms, with or without
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
Represents a property, i.e. property definition and value.
"""


from datafinder.core.configuration.properties.property_type import ObjectType
from datafinder.core.error import PropertyError


__version__ = "$Revision-Id:$" 


class Property(object):
    """
    Represents a property, i.e. property definition and value.
    """

    def __init__(self, propertyDefinition, value):
        """
        Constructor.

        @param propertyDefinition: Describes the property by name, identifier, restrictions, etc.
        @type propertyDefinition: L{PropertyDefinition<datafinder.core.configuration.properties.property_definition.PropertyDefinition>}
        @param value: Value of the property.
        @type value: C{object}
        """
        
        self._propertyDefinition = propertyDefinition
        self._additionalValueRepresentations = list()
        self._value = None
        self.value = value
        
    def __getPropertyIdentifier(self):
        """ Getter of the property identifier. """
        
        return self._propertyDefinition.identifier
    
    identifier = property(__getPropertyIdentifier)
        
    def __getPropertyDefinition(self):
        """ Getter for the property definition. """
        
        return self._propertyDefinition
    
    propertyDefinition = property(__getPropertyDefinition)
        
    def __getValue(self):
        """ Getter of the value attribute. """
        
        if isinstance(self._value, type(dict())):
            print self._propertyDefinition.propertyType.instance.fromDict(self._value)
            print self._propertyDefinition.propertyType.instance.fromDict(self._value).__dict__
            try:
                return self._propertyDefinition.propertyType.instance.fromDict(self._value)
            except AttributeError, error:
                raise PropertyError("Cannot get value. Reason: %s" % error)
        else:
            return self._value
        
    def __setValue(self, value):
        """ Setter of the value attribute. """        

        self.propertyDefinition.validate(value)
        self._additionalValueRepresentations = list()
        self._value = value
    
    value = property(__getValue, __setValue)

    def __getAdditionalValueRepresentations(self):
        """ Returns the additional supported value representations. """
        
        return self._additionalValueRepresentations[:]

    additionalValueRepresentations = property(__getAdditionalValueRepresentations)

    def __repr__(self):
        """ Returns the representation. """
        
        return repr(self.propertyDefinition) + ": " + repr(self.value)
    
    def __cmp__(self, other):
        """ Implements comparison of two instances. """
        
        try:
            return cmp(self.propertyDefinition.identifier, other.propertyDefinition.identifier)
        except AttributeError:
            return 1
        
    def toPersistenceFormat(self):
        value = self.value
        if isinstance(self._propertyDefinition.propertyType, ObjectType):
            try:
                value = self.value.toDict()
            except AttributeError, error:
                raise PropertyError("Cannot convert to persistence format. Reason: %s" % error)
        return self.identifier, value
        
    @staticmethod
    def create(propertyDefinition, persistedValue):
        """ 
        Creates a property from persistence format.
        
        @param propertyDefinition: Describes the property by name, identifier, restrictions, etc.
        @type propertyDefinition: L{PropertyDefinition<datafinder.core.configuration.properties.property_definition.PropertyDefinition>}
        @param persistedValue: Value of the property in persistence format.
        @type persistedValue: L{MetadataValue<datafinder.persistence.metadata.value_mapping.MetadataValue>}
        """
    
        additionalValueRepresentations = list()
        foundValidRepresentation = False
        valueRepresentations = persistedValue.guessRepresentation()
        for valueRepresentation in valueRepresentations:
            try:
                
                if isinstance(valueRepresentation, dict): #AttributeError?
                    classObj = propertyDefinition.propertyType.cls
                    valueRepresentation = classObj.fromDict(valueRepresentation)
                propertyDefinition.validate(valueRepresentation)
                if not foundValidRepresentation:
                    value = valueRepresentation
                    foundValidRepresentation = True
                else:
                    additionalValueRepresentations.append(valueRepresentation)
            except PropertyError:
                continue
        if not foundValidRepresentation:
            value = propertyDefinition.defaultValue
        result = Property(propertyDefinition, value)
        result._additionalValueRepresentations = additionalValueRepresentations
        return result
