# -*-coding:UTF-8 -*
"""
Base Class for AIL Objects
"""

##################################
# Import External packages
##################################
import os
import logging.config
import sys
from abc import ABC, abstractmethod
from pymisp import MISPObject

# from flask import url_for

sys.path.append(os.environ['AIL_BIN'])
##################################
# Import Project packages
##################################
from lib import ail_logger
from lib import Tag
from lib.ConfigLoader import ConfigLoader
from lib import Duplicate
from lib.correlations_engine import get_nb_correlations, get_correlations, add_obj_correlation, delete_obj_correlation, delete_obj_correlations, exists_obj_correlation, is_obj_correlated, get_nb_correlation_by_correl_type, get_obj_inter_correlation
from lib.Investigations import is_object_investigated, get_obj_investigations, delete_obj_investigations
from lib.relationships_engine import get_obj_nb_relationships, add_obj_relationship
from lib.Language import get_obj_translation
from lib.Tracker import is_obj_tracked, get_obj_trackers, delete_obj_trackers

logging.config.dictConfig(ail_logger.get_config(name='ail'))

config_loader = ConfigLoader()
# r_cache = config_loader.get_redis_conn("Redis_Cache")
r_object = config_loader.get_db_conn("Kvrocks_Objects")
config_loader = None

class AbstractObject(ABC):
    """
    Abstract Object
    """

    def __init__(self, obj_type, id, subtype=None):
        """ Abstract for all the AIL object

        :param obj_type: object type (item, ...)
        :param id: Object ID
        """
        self.id = id
        self.type = obj_type
        self.subtype = subtype

        self.logger = logging.getLogger(f'{self.__class__.__name__}')

    def get_id(self):
        return self.id

    def get_type(self):
        return self.type

    def get_subtype(self, r_str=False):
        if not self.subtype:
            if r_str:
                return ''
        return self.subtype

    def get_global_id(self):
        return f'{self.get_type()}:{self.get_subtype(r_str=True)}:{self.get_id()}'

    def get_default_meta(self, tags=False, link=False):
        dict_meta = {'id': self.get_id(),
                     'type': self.get_type(),
                     'subtype': self.get_subtype(r_str=True)}
        if tags:
            dict_meta['tags'] = self.get_tags()
        if link:
            dict_meta['link'] = self.get_link()
        return dict_meta

    def _get_field(self, field):
        if self.subtype is None:
            return r_object.hget(f'meta:{self.type}:{self.id}', field)
        else:
            return r_object.hget(f'meta:{self.type}:{self.get_subtype(r_str=True)}:{self.id}', field)

    def _set_field(self, field, value):
        if self.subtype is None:
            return r_object.hset(f'meta:{self.type}:{self.id}', field, value)
        else:
            return r_object.hset(f'meta:{self.type}:{self.get_subtype(r_str=True)}:{self.id}', field, value)

    ## Tags ##
    def get_tags(self, r_list=False):
        tags = Tag.get_object_tags(self.type, self.id, self.get_subtype(r_str=True))
        if r_list:
            tags = list(tags)
        return tags

    def add_tag(self, tag):
        Tag.add_object_tag(tag, self.type, self.id, subtype=self.get_subtype(r_str=True))

    def is_tags_safe(self, tags=None):
        if not tags:
            tags = self.get_tags()
        return Tag.is_tags_safe(tags)

    ## -Tags- ##

    @abstractmethod
    def get_content(self):
        """
        Get Object Content
        """
        pass

    ## Duplicates ##
    def get_duplicates(self):
        return Duplicate.get_obj_duplicates(self.type, self.get_subtype(r_str=True), self.id)

    def add_duplicate(self, algo, similarity, id_2):
        return Duplicate.add_obj_duplicate(algo, similarity, self.type, self.get_subtype(r_str=True), self.id, id_2)
    ## -Duplicates- ##

    ## Investigations ##

    def is_investigated(self):
        if not self.subtype:
            is_investigated = is_object_investigated(self.id, self.type)
        else:
            is_investigated = is_object_investigated(self.id, self.type, self.subtype)
        return is_investigated

    def get_investigations(self):
        if not self.subtype:
            investigations = get_obj_investigations(self.id, self.type)
        else:
            investigations = get_obj_investigations(self.id, self.type, self.subtype)
        return investigations

    def delete_investigations(self):
        if not self.subtype:
            unregistered = delete_obj_investigations(self.id, self.type)
        else:
            unregistered = delete_obj_investigations(self.id, self.type, self.subtype)
        return unregistered

    ## -Investigations- ##

    ## Trackers ##

    def is_tracked(self):
        return is_obj_tracked(self.type, self.subtype, self.id)

    def get_trackers(self):
        return get_obj_trackers(self.type, self.subtype, self.id)

    def delete_trackers(self):
        return delete_obj_trackers(self.type, self.subtype, self.id)

    ## -Trackers- ##

    def _delete(self):
        # DELETE TAGS
        Tag.delete_object_tags(self.type, self.get_subtype(r_str=True), self.id)
        # remove from tracker
        self.delete_trackers()
        # remove from retro hunt currently item only TODO
        # remove from investigations
        self.delete_investigations()
        # Delete Correlations
        delete_obj_correlations(self.type, self.get_subtype(r_str=True), self.id)

    @abstractmethod
    def delete(self):
        """
        Delete Object: used for the Data Retention
        """
        pass

    @abstractmethod
    def exists(self):
        """
        Exists Object
        """
        pass

    @abstractmethod
    def get_meta(self, options=set()):
        """
        get Object metadata
        """
        pass

    @abstractmethod
    def get_link(self, flask_context=False):
        pass

    @abstractmethod
    def get_svg_icon(self):
        """
        Get object svg icon
        """
        pass

    @abstractmethod
    def get_misp_object(self):
        pass

    @staticmethod
    def get_misp_object_tags(misp_obj):
        """
        :type misp_obj: MISPObject
        """
        if misp_obj.attributes:
            misp_tags = misp_obj.attributes[0].tags
            tags = []
            for tag in misp_tags:
                tags.append(tag.name)
            return tags
        else:
            return []

    ## Correlation ##

    def _get_external_correlation(self, req_type, req_subtype, req_id, obj_type):
        """
        Get object correlation
        """
        return get_correlations(req_type, req_subtype, req_id, filter_types=[obj_type])

    def get_correlation(self, obj_type):
        """
        Get object correlation
        """
        return get_correlations(self.type, self.subtype, self.id, filter_types=[obj_type])

    def get_correlations(self, filter_types=[], unpack=False):
        """
        Get object correlations
        """
        return get_correlations(self.type, self.subtype, self.id, filter_types=filter_types, unpack=unpack)

    def get_nb_correlation(self, correl_type):
        return get_nb_correlation_by_correl_type(self.type, self.get_subtype(r_str=True), self.id, correl_type)

    def get_nb_correlations(self, filter_types=[]):
        return get_nb_correlations(self.type, self.subtype, self.id, filter_types=filter_types)

    def add_correlation(self, type2, subtype2, id2):
        """
        Add object correlation
        """
        add_obj_correlation(self.type, self.subtype, self.id, type2, subtype2, id2)

    def exists_correlation(self, type2):
        """
        Check if an object is correlated
        """
        return exists_obj_correlation(self.type, self.subtype, self.id, type2)

    def is_correlated(self, type2, subtype2, id2):
        """
        Check if an object is correlated by another object
        """
        return is_obj_correlated(self.type, self.subtype, self.id, type2, subtype2, id2)

    def are_correlated(self, object2):
        """
        Check if an object is correlated with another Object
        :type object2 AbstractObject
        """
        return is_obj_correlated(self.type, self.subtype, self.id,
                                 object2.get_type(), object2.get_subtype(r_str=True), object2.get_id())

    def get_correlation_iter(self, obj_type2, subtype2, obj_id2, correl_type):
        return get_obj_inter_correlation(self.type, self.get_subtype(r_str=True), self.id, obj_type2, subtype2, obj_id2, correl_type)

    def get_correlation_iter_obj(self, object2, correl_type):
        return self.get_correlation_iter(object2.get_type(), object2.get_subtype(r_str=True), object2.get_id(), correl_type)

    def delete_correlation(self, type2, subtype2, id2):
        """
        Get object correlations
        """
        delete_obj_correlation(self.type, self.subtype, self.id, type2, subtype2, id2)

    ## -Correlation- ##

    ## Relationship ##

    def get_nb_relationships(self, filter=[]):
        return get_obj_nb_relationships(self.get_global_id())

    def add_relationship(self, obj2_global_id, relationship, source=True):
        # is source
        if source:
            print(self.get_global_id(), obj2_global_id, relationship)
            add_obj_relationship(self.get_global_id(), obj2_global_id, relationship)
        # is target
        else:
            add_obj_relationship(obj2_global_id, self.get_global_id(), relationship)

    ## -Relationship- ##

    ## Translation ##

    def translate(self, content=None, field='', source=None, target='en'):
        global_id = self.get_global_id()
        if not content:
            content = self.get_content()
        return get_obj_translation(global_id, content, field=field, source=source, target=target)

    ## -Translation- ##

    ## Parent ##

    def is_parent(self):
        return r_object.exists(f'child:{self.type}:{self.get_subtype(r_str=True)}:{self.id}')

    def is_children(self):
        return r_object.hexists(f'meta:{self.type}:{self.get_subtype(r_str=True)}:{self.id}', 'parent')

    def get_parent(self):
        return r_object.hget(f'meta:{self.type}:{self.get_subtype(r_str=True)}:{self.id}', 'parent')

    def get_childrens(self):
        return r_object.smembers(f'child:{self.type}:{self.get_subtype(r_str=True)}:{self.id}')

    def set_parent(self, obj_type=None, obj_subtype=None, obj_id=None, obj_global_id=None):  # TODO # REMOVE ITEM DUP
        if not obj_global_id:
            if obj_subtype is None:
                obj_subtype = ''
            obj_global_id = f'{obj_type}:{obj_subtype}:{obj_id}'
        r_object.hset(f'meta:{self.type}:{self.get_subtype(r_str=True)}:{self.id}', 'parent', obj_global_id)
        r_object.sadd(f'child:{obj_global_id}', self.get_global_id())

    def add_children(self, obj_type=None, obj_subtype=None, obj_id=None, obj_global_id=None): # TODO # REMOVE ITEM DUP
        if not obj_global_id:
            if obj_subtype is None:
                obj_subtype = ''
            obj_global_id = f'{obj_type}:{obj_subtype}:{obj_id}'
        r_object.sadd(f'child:{self.type}:{self.get_subtype(r_str=True)}:{self.id}', obj_global_id)
        r_object.hset(f'meta:{obj_global_id}', 'parent', self.get_global_id())

    ## others objects ##
    def add_obj_children(self, parent_global_id, son_global_id):
        r_object.sadd(f'child:{parent_global_id}', son_global_id)
        r_object.hset(f'meta:{son_global_id}', 'parent', parent_global_id)

    ## Parent ##
