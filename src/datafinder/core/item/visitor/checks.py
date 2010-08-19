# pylint: disable-msg=W0612,R0901,W0212
# W0612: Unused variable -> ignored due to "accept" attributes of visiting methods
# R0901: Too many ancestors -> Needed to efficiently implementing ActionCheckTreeWalker
# W0212: Accessing protected member of the item class -> temporary workaround
#
# Created: Michael Meinel <michael.meinel@dlr.de>
# Changed: $Id: checks.py 4596 2010-04-10 21:45:52Z schlauch $
# 
# Copyright (c) 2008, German Aerospace Center (DLR)
# All rights reserved.
# 
# 
# http://www.dlr.de/datafinder/
# 


"""
This module implements some sanity checks based on the visitor/tree walker classes
defined in this package.
"""


from datafinder.core.error import PrivilegeError
from datafinder.core.item.base import ItemBase
from datafinder.core.item.collection import ItemRoot, ItemCollection
from datafinder.core.item.data_persister import constants
from datafinder.core.item.leaf import ItemLeaf
from datafinder.core.item.link import ItemLink
from datafinder.core.item.privileges.privilege import ALL_PRIVILEGE, WRITE_PRIVILEGE
from datafinder.core.item.visitor.base import ItemTreeWalkerBase, VisitSlot


__version__ = "$LastChangedRevision: 4596 $"


class ActionCheckVisitor(object):
    """
    This class performs sanity checks on a given L{ItemBase<datafinder.core.item.base.ItemBase>}.
    
    It checks what capabilities this item has (e.g. can be read/write/deleted etc.).
    
    To ensure a special capability, you may use the convenience C{canDo} methods. But as those
    re-check the item each time they are called, it is better to access the C{capabilites} dictionary
    in conjunction with the L{check<datafinder.core.item.visitor.checks.ActionCheckTreeWalker.check>}
    method if you want to query different capabilities at once.
    
    @cvar CAPABILITY_ADD_CHILDREN: Other items can be added below this item.
    @cvar CAPABILITY_DELETE: The item can be deleted (or does not exist yet).
    @cvar CAPABILITY_COPY: The item can be copied.
    @cvar CAPABILITY_MOVE: The item can be moved.
    @cvar CAPABILITY_STORE: The associated data for the item can be stored.
    @cvar CAPABILITY_RERTRIEVE: The associated data for the item can be retrieved.
    @cvar CAPABILITY_ARCHIVE: The given item can be archived.
    @cvar CAPABILITY_SEARCH: Searches can be performed using the given item.
    @cvar CAPABILITY_RETRIEVE_PROPERTIES: Properties of the item can be retrieved.
    @cvar CAPABILITY_STORE_PROPERTIES: Properties of the given item can be written.
    """
    
    
    CAPABILITY_ADD_CHILDREN = "canAddChildren"
    CAPABILITY_DELETE = "delete"
    CAPABILITY_COPY = "copy"
    CAPABILITY_MOVE = "move"
    CAPABILITY_STORE = "storeData"
    CAPABILITY_RETRIEVE = "retrieveData"
    CAPABILITY_ARCHIVE = "archive"
    CAPABILITY_SEARCH = "search"
    CAPABILITY_RETRIEVE_PROPERTIES = "retrieveProperties"
    CAPABILITY_STORE_PROPERTIES = "storeProperties"
    
    
    def __init__(self, resolveLinks=False, hasCustomMetadataSupport=False, hasSearchSupport=False):
        """ Constructor. """

        self.resolveLinks = resolveLinks
        self._hasCustomMetadataSupport = hasCustomMetadataSupport
        self._hasSearchSupport = hasSearchSupport
        
        self.capabilities = dict()
        self._path = list()
    
    def check(self, item):
        """
        Run checks.
        
        This method cares for resetting the capabilities dictionary first. It then triggers the visitor
        to check the items capabilities.
        
        @param item: The item to be checked
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self._initCapabilities()
        if not item._ignoreChecks: # W0212
            self.handle(item)
    
    def _initCapabilities(self):
        """ Initializes the capabilities. """
        
        self.capabilities = {
            ActionCheckTreeWalker.CAPABILITY_ADD_CHILDREN: True,
            ActionCheckTreeWalker.CAPABILITY_DELETE: True,
            ActionCheckTreeWalker.CAPABILITY_COPY: True,
            ActionCheckTreeWalker.CAPABILITY_MOVE: True,
            ActionCheckTreeWalker.CAPABILITY_STORE: True,
            ActionCheckTreeWalker.CAPABILITY_RETRIEVE: True,
            ActionCheckTreeWalker.CAPABILITY_ARCHIVE: True,
            ActionCheckTreeWalker.CAPABILITY_SEARCH: self._hasSearchSupport,
            ActionCheckTreeWalker.CAPABILITY_RETRIEVE_PROPERTIES: self._hasCustomMetadataSupport,
            ActionCheckTreeWalker.CAPABILITY_STORE_PROPERTIES: self._hasCustomMetadataSupport
        }
    
    def _disable(self, caps):
        """
        Helper method that disables the given capabilities.
        """
    
        for capability in caps:
            self.capabilities[capability] = False
    
    def handleDataNode(self, item):
        """
        Implementation of the C{handle} slot for any items except links.
        
        It enforces that only valid combinations of state, strategy and location are given
        and cares for setting the capabilities dictionary correctly. If one of the sanity checks
        fail, a C{ValueError} along with an expressive error message is raised. 
        
        @param item: The item which should be checked.
        @type item: L{ItemRoot<datafinder.core.item.collection.ItemRoot>},
                    L{ItemCollection<datafinder.core.item.collection.ItemCollection>} or
                    L{ItemLeaf<datafinder.core.item.leaf.ItemLeaf>}
        @raise ValueError: Any sanity check failed on the given item or any of its child.
        """
        
        if item.isRoot:
            self._disable(self.capabilities.keys())
            self.capabilities[self.CAPABILITY_ADD_CHILDREN] = item.fileStorer.canAddChildren
            self.capabilities[self.CAPABILITY_SEARCH] = self._hasSearchSupport
        else:
            self._checkDataState(item)
            self._checkPrivileges(item)
        if not (item.isCollection and item.state == constants.ITEM_STATE_NULL):
            self._disable((ActionCheckVisitor.CAPABILITY_ARCHIVE,))
            
    handleDataNode.accept = ItemRoot, ItemCollection, ItemLeaf
    
    def _checkDataState(self, item):
        """ Helper method checking the data state of the item. """
    
        state = item.state
        # Capability constraints for items in state INACCESSIBLE or NULL
        #  - must not store data
        #  - must not retrieve data
        #  - (i.e. may not access data)
        if state == constants.ITEM_STATE_INACCESSIBLE \
           or state == constants.ITEM_STATE_NULL:
            self._disable((ActionCheckVisitor.CAPABILITY_STORE,
                           ActionCheckVisitor.CAPABILITY_RETRIEVE))
        # Capability constraints for items in state MIGRATED
        #  - must not be accessed
        elif state == constants.ITEM_STATE_MIGRATED \
             or state == constants.ITEM_STATE_UNSUPPORTED_STORAGE_INTERFACE:
            self._disable(self.capabilities.keys())
        # Capability constraints for items in state ARCHIVE
        #  - must not change properties
        elif state == constants.ITEM_STATE_ARCHIVED:
            self._disable((ActionCheckVisitor.CAPABILITY_STORE_PROPERTIES, ))
        # Capability constraints for items in state ARCHIVE MEMBER
        #  - must not delete data
        #  - must not store data
        #  - addition sub-items is optional
        #  - must not change properties
        #  - must not be copied or moved 
        elif state == constants.ITEM_STATE_ARCHIVED_MEMBER:
            self._disable((ActionCheckVisitor.CAPABILITY_COPY, 
                           ActionCheckVisitor.CAPABILITY_MOVE,
                           ActionCheckVisitor.CAPABILITY_DELETE,
                           ActionCheckVisitor.CAPABILITY_STORE,
                           ActionCheckVisitor.CAPABILITY_STORE_PROPERTIES))
        # Capability constraints for items in state READONLY ARCHIVE
        #  - must not delete data
        #  - must not store data
        #  - must not change properties
        elif state == constants.ITEM_STATE_ARCHIVED_READONLY:
            self._disable((ActionCheckVisitor.CAPABILITY_STORE,
                           ActionCheckVisitor.CAPABILITY_DELETE,
                           ActionCheckVisitor.CAPABILITY_STORE_PROPERTIES))

    def _checkPrivileges(self, item):
        """ Helper method checking the privileges. """
        
        try:
            if not item is None and not (ALL_PRIVILEGE in item.privileges or WRITE_PRIVILEGE in item.privileges):
                self._disable((ActionCheckVisitor.CAPABILITY_ADD_CHILDREN,
                               ActionCheckVisitor.CAPABILITY_STORE,
                               ActionCheckVisitor.CAPABILITY_MOVE,
                               ActionCheckVisitor.CAPABILITY_DELETE,
                               ActionCheckVisitor.CAPABILITY_STORE_PROPERTIES))
        except PrivilegeError:
            self._disable((ActionCheckVisitor.CAPABILITY_ADD_CHILDREN,
                           ActionCheckVisitor.CAPABILITY_STORE,
                           ActionCheckVisitor.CAPABILITY_MOVE,
                           ActionCheckVisitor.CAPABILITY_DELETE,
                           ActionCheckVisitor.CAPABILITY_STORE_PROPERTIES))
    
    def handleLink(self, item):
        """
        Implementation of the C{handle} slot for L{ItemLink<datafinder.core.item.link.ItemLink>}.
        """
        
        if self.resolveLinks and item.name not in self._path:
            item = item.linkTarget
            self.handle(item)
        else:
            self._checkDataState(item)
            self._checkPrivileges(item)
    handleLink.accept = ItemLink,
    
    def handleBase(self, item):
        """
        Implementation of the C{handle} slot for L{ItemBase<datafinder.core.item.base.ItemBase>}.
        """
        
        if item.isLink:
            self.handleLink(item)
        else:
            self.handleDataNode(item)
    handleBase.accept = ItemBase,
    
    handle = VisitSlot(handleDataNode, handleLink, handleBase)
    
    def canAddChildren(self, item):
        """
        Convenience method to check whether an item can be created below.
        
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_ADD_CHILDREN]
    
    def canDelete(self, item):
        """
        Convenience method to check whether an item can be deleted.
        
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_DELETE]
    
    def canCopy(self, item):
        """
        Convenience method to check whether an item can be copied.
        
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_COPY]
    
    def canMove(self, item):
        """
        Convenience method to check whether an item can be moved.
        
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_MOVE]
    
    def canStoreData(self, item):
        """
        Convenience method to check whether the associated data can be stored using this item.
        
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_STORE]
    
    def canRetrieveData(self, item):
        """
        Convenience method to check whether the associated data can be retrieved using this item.
        
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_RETRIEVE]
    
    def canArchive(self, item):
        """
        Convenience method to check whether an item can be archived.
        
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_ARCHIVE]
    
    def canSearch(self, item):
        """
        Convenience method to check whether an item can be searched.
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_SEARCH]

    def canRetrieveProperties(self, item):
        """
        Convenience method to check whether an item`s properties can be retrieved.
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_RETRIEVE_PROPERTIES]

    def canStoreProperties(self, item):
        """
        Convenience method to check whether an item`s properties can be written.
        @note: The sanity checks are run again when this method is called.
        
        @param item: The item to be checked.
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self.check(item)
        return self.capabilities[ActionCheckVisitor.CAPABILITY_STORE_PROPERTIES]

    
class ActionCheckTreeWalker(ItemTreeWalkerBase, ActionCheckVisitor):
    """
    This class does essentially the same as
    L{ActionCheckVisitor<datafinder.core.item.visitor.checks.ActionCheckVisitor>} but extends the checks
    to any children of the item due to its nature as tree walker.
    
    @ivar handle: Visitor slot that does the actual handling.
    @type handle: C{VisitSlot}
    """

    def __init__(self, resolveLinks=False, hasCustomMetadataSupport=False, hasSearchSupport=False):
        """
        Constructor.
        
        @param resolveLinks: Select whether links should be resolved or not.
        @type resolveLinks: boolean
        """
        
        ActionCheckVisitor.__init__(self, resolveLinks, hasCustomMetadataSupport, hasSearchSupport)
        ItemTreeWalkerBase.__init__(self, mode=-1) # enforce pre-order scheme
        self.affectedItems = list()
        self._path = list()
    
    def check(self, item):
        """
        Run checks.
        
        This method cares for resetting the capabilities dictionary first. It then starts walking
        the tree and updates the capabilities for each node it hits.
        
        @param item: The item to be checked
        @type item: L{ItemBase<datafinder.core.item.base.ItemBase>}
        """
        
        self._initCapabilities()
        if not item._ignoreChecks: # W0212
            self.affectedItems = list()
            self.walk(item)
            self.affectedItems.remove(item)

    def walk(self, node):
        """
        Re-implementation of the C{walk} slot for any item.
        
        Simply cares for appending current node to the list of affected items and calling
        the base implementation of this slot.
        """
        
        if node.state in [constants.ITEM_STATE_ARCHIVED, constants.ITEM_STATE_ARCHIVED_READONLY]: 
            currentCapabilities = self.capabilities.copy() #ignoring capabilities of archive members

        self.affectedItems.append(node)
        super(ActionCheckTreeWalker, self).walk(node)
        
        if node.state in [constants.ITEM_STATE_ARCHIVED, constants.ITEM_STATE_ARCHIVED_READONLY]:
            self.capabilities = currentCapabilities
            self.handle(node)
    
    def handleLink(self, item):
        """
        Implementation of the C{handle} slot for L{ItemLink<datafinder.core.item.link.ItemLink>}.
        """
        
        if self.resolveLinks and item.name not in self._path:
            self._path.append(item.name)
            item = item.linkTarget
            self.walk(item)
            self._path = self._path[:-1]
    handleLink.accept = ItemLink,
    
    handle = VisitSlot(handleLink, inherits="handle")
    

class ItemCapabilityChecker(object):
    """ 
    Convenience class providing the can* methods of C{ActionCheckVisitor}.
    The item is not passed to the method but to the constructor.
    """
    
    def __init__(self, item, hasCustomMetadataSupport=False, hasSearchSupport=False):
        """ Constructor. """
        
        self._item = item
        self._actionCheckVisitor = ActionCheckVisitor(False, hasCustomMetadataSupport, hasSearchSupport)
        
    def _decorateMethodWithItemInstance(self, method):
        """ Returns a method decorated with the item instance. """
        
        def _decoratedMethod():
            """ The decorated method implementation. """
            
            return method(self._item)
        return property(_decoratedMethod).fget()

    def __getattr__(self, name):
        """ The implementation does the decoration magic. """
        
        if hasattr(self._actionCheckVisitor, name):
            return self._decorateMethodWithItemInstance(getattr(self._actionCheckVisitor, name))
        else:
            raise AttributeError("AttributeError: '%s' object has no attribute '%s'" % (str(self), name))
