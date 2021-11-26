from io import BytesIO
from lazy import lazy
from lxml.html import fromstring as parse_html
from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import LargeBinary
from sqlalchemy import Unicode
from sqlalchemy import TIMESTAMP
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapper
from sqlalchemy.orm import backref
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zeit.connector.interfaces import DeleteProperty
from zope.sqlalchemy import register
import datetime
import os
import secrets
import six
import zeit.connector.interfaces
import zeit.connector.resource
import zope.interface


HTTPD_UNIXDIRECTORY = 'httpd/unix-directory'
RESOURCE_TYPE_PROPERTY = zeit.connector.interfaces.RESOURCE_TYPE_PROPERTY
RFC3339_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# engine = create_engine("postgresql:///vivi", echo=True, echo_pool=True, future=True)
# engine = create_engine("postgresql:///vivi", echo=True, future=True)
engine = create_engine("postgresql:///vivi", echo_pool=True, future=True)
# engine = create_engine("postgresql://?service=vivi-devel", echo_pool=True, future=True)
# engine = create_engine("postgresql:///vivi", future=True)

DBSession = scoped_session(sessionmaker(bind=engine))
register(DBSession)


def _index_object(session, instance):
    # store a "hard" reference to the object on the session,
    # otherwise gc will remove the instances from the weak identity_map
    # during the request, which would cause a re-fetch from the db
    # see https://github.com/sqlalchemy/sqlalchemy/discussions/7246
    set_ = session.info.get("strong_set", None)
    if not set_:
        session.info["strong_set"] = set_ = set()

    set_.add(instance)


@event.listens_for(Mapper, "load")
def object_loaded(instance, ctx):
    _index_object(ctx.session, instance)


@event.listens_for(DBSession, "after_attach")
def index_object(session, instance):
    _index_object(session, instance)


metadata_object = MetaData()

BaseObject = declarative_base(metadata=metadata_object)


class StorageItem(BaseObject):
    __tablename__ = "storage"

    path = Column(Unicode, primary_key=True)
    blob = Column(LargeBinary, nullable=False)
    properties = Column(JSONB, nullable=False)

    def __repr__(self):
        return f"<{self.__class__.__name__} path={self.path}>"


class CanonicalPath(BaseObject):
    __tablename__ = "canonical_path"

    id = Column(Unicode, primary_key=True)
    path = Column(
        Unicode,
        ForeignKey(StorageItem.path, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=True)
    item = relationship(StorageItem, lazy='joined', backref=backref('cpaths', lazy='joined'))

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id} path={self.path}>"


class Lock(BaseObject):
    __tablename__ = "locks"

    path = Column(
        Unicode,
        ForeignKey(StorageItem.path, onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True)
    principal = Column(Unicode, nullable=False)
    until = Column(TIMESTAMP(timezone=True), nullable=False)
    token = Column(Unicode, nullable=False)


def _get_resource_type(properties):
    __traceback_info__ = (id, )
    r_type = properties.get(RESOURCE_TYPE_PROPERTY)
    if r_type is None:
        dav_type = properties.get(('resourcetype', 'DAV:'), '')
        content_type = properties.get(('getcontenttype', 'DAV:'), '')
        __traceback_info__ = (id, dav_type, content_type)
        if dav_type and 'collection' in dav_type:
            r_type = 'collection'
        elif content_type.startswith('image/'):
            r_type = 'image'
        else:
            r_type = 'unknown'
    return r_type


def _convert_properties_to_dict(properties):
    # properties have tuples of the form (key, namespace) as keys,
    # which doesn't work as json, so create a nested dict instead
    metadata = {}
    for (k, ns), v in properties.items():
        if isinstance(v, datetime.datetime):
            if k == 'cached-time':
                # ignore property from zeo cache
                continue
            raise RuntimeError("datetime %r %r" % (k, v))
        metadata.setdefault(ns, {})[k] = v
    return metadata


def _convert_properties_from_dict(metadata):
    # properties have tuples of the form (key, namespace) as keys,
    # which doesn't work as json, so we transform from a nested dict
    properties = {}
    for ns, d in metadata.items():
        for k, v in d.items():
            properties[(k, ns)] = v
    return properties


def _remove_deleted_metadata(metadata):
    for ns, d in metadata.items():
        for k, v in list(d.items()):
            if v is DeleteProperty:
                del d[k]


@zope.interface.implementer(zeit.connector.interfaces.ICachingConnector)
class CachingConnector(object):
    def __init__(self, roots={}, prefix=u'http://xml.zeit.de/'):
        print("    postgresql.Connector.__init__", roots, prefix)
        roots.setdefault('postgresql', 'vivi')
        self._roots = roots
        self._prefix = prefix
        metadata_object.create_all(engine)

    def _id2path(self, id):
        if not id.startswith(self._prefix):
            raise ValueError("Bad id %r (prefix is %r)" % (id, self._prefix))
        return id[len(self._prefix):]

    @lazy
    def DAVConnector(self):
        import zeit.connector.connector
        return zeit.connector.connector.Connector

    @lazy
    def _webdav_connector(self):
        print("    postgresql.Connector._webdav_connector")
        connector = self.DAVConnector(self._roots, self._prefix)
        connector.from_postgresql = True
        return connector

    def _webdav_get(self, session, id):
        wdc = self._webdav_connector
        cid = self._webdav_connector._get_cannonical_id(id)
        path = self._id2path(cid)
        try:
            properties = wdc._get_resource_properties(cid)
        except (zeit.connector.dav.interfaces.DAVNotFoundError,
                zeit.connector.dav.interfaces.DAVBadRequestError):
            print(cid, "Not found")
            # cache not found
            session.add(CanonicalPath(id=id, path=None))
            raise KeyError(
                "The resource %r does not exist." % six.text_type(cid))
        metadata = _convert_properties_to_dict(properties)
        body = wdc._get_resource_body(cid)
        session.add(StorageItem(
            path=path,
            blob=body.read(),
            properties=metadata))
        session.add(CanonicalPath(id=cid, path=path))
        if id != cid:
            session.add(CanonicalPath(id=id, path=path))
        result = wdc[id]
        print("    DAV", id, result)
        return result

    def _db_get(self, session, id):
        cpath = session.get(CanonicalPath, id)
        if cpath is None:
            cid = self._webdav_connector._get_cannonical_id(id)
            cpath = session.get(CanonicalPath, cid)
            if cpath is None:
                return None
            session.add(CanonicalPath(id=id, path=cpath.item.path))
        if cpath.path is None:
            raise KeyError(
                "The resource %r does not exist." % six.text_type(id))
        item = cpath.item
        properties = _convert_properties_from_dict(item.properties)
        resource_type = _get_resource_type(properties)
        content_type = properties.get(('getcontenttype', 'DAV:'))
        body = BytesIO(item.blob)
        path = item.path
        cid = self._prefix + path
        result = zeit.connector.resource.CachedResource(
            six.text_type(cid),
            self.DAVConnector._id_splitlast(cid)[1].rstrip('/'),
            resource_type,
            lambda: properties,
            lambda: body,
            content_type=content_type)
        # print("    DB", path, result)
        return result

    def __getitem__(self, id):
        session = DBSession()
        result = self._db_get(session, id)
        if result is None:
            result = self._webdav_get(session, id)
        return result

    def listCollection(self, id):
        body = self[id].data.read()
        tree = parse_html(body)
        result = sorted(
            (x.text.rstrip('/'), id + x.text)
            for x in tree.cssselect('td > a')
            if x.text != 'Parent Directory' and not x.attrib['href'].startswith('/'))
        _result = sorted(self._webdav_connector.listCollection(id))
        if result != _result:
            print("    listCollection (differences)", id, set(result).symmetric_difference(_result))
            print(body)
            return _result
        # print("    listCollection", id, result)
        return result

    def add(self, obj, verify_etag=True):
        result = self._webdav_connector.add(obj, verify_etag=verify_etag)
        print("    add", obj, verify_etag, result)
        return result

    def lock(self, id, principal, until):
        result = self._webdav_connector.lock(id, principal, until)
        print("    lock", id, principal, until, result)
        return result

    def locked(self, id):
        # return (None, None, False)
        return self._webdav_connector.locked(id)

    def unlock(self, id, locktoken=None, invalidate=True):
        result = self._webdav_connector.unlock(
            id, locktoken=locktoken, invalidate=invalidate)
        print("    unlock", id, locktoken, invalidate, result)
        return result

    @classmethod
    def factory(cls):
        import zope.app.appsetup.product
        print("    postgresql.Connector.factory")
        config = zope.app.appsetup.product.getProductConfiguration(
            'zeit.connector')
        return cls({
            'default': config['document-store'],
            'search': config['document-store-search']})


class Root:
    contentType = HTTPD_UNIXDIRECTORY
    type = 'collection'
    data = BytesIO(b'')
    properties = {}

    def __init__(self, prefix):
        self.id = prefix


@zope.interface.implementer(zeit.connector.interfaces.ICachingConnector)
class Connector(object):
    def __init__(self, roots={}, prefix=u'http://xml.zeit.de/'):
        print("    postgresql.Connector.__init__", roots, prefix)
        roots.setdefault('postgresql', 'vivi')
        self._roots = roots
        self._prefix = prefix
        metadata_object.create_all(engine)
        try:
            self[prefix]
        except KeyError:
            self.add(Root(prefix))

    def _id2path(self, id):
        if not id.startswith(self._prefix):
            raise ValueError("Bad id %r (prefix is %r)" % (id, self._prefix))
        return id[len(self._prefix):]

    @lazy
    def DAVConnector(self):
        import zeit.connector.connector
        return zeit.connector.connector.Connector

    def listCollection(self, id):
        # if id != self._prefix:
        #     import pdb; pdb.set_trace()
        try:
            obj = self[id]
        except KeyError:
            print("    listCollection", id, "Not Found")
            return []
        body = obj.data.read()
        if not body:
            print("    listCollection", id, [])
            return []
        tree = parse_html(body)
        result = sorted(
            (x.text.rstrip('/'), os.path.join(id, x.text))
            for x in tree.cssselect('td > a')
            if x.text != 'Parent Directory' and not x.attrib['href'].startswith('/'))
        print("    listCollection", id, result)
        return result

    def __contains__(self, id):
        session = DBSession()
        cpath = session.get(CanonicalPath, id)
        result = cpath is not None
        print("    contains", id, result)
        return result

    def __delitem__(self, id):
        print("    delitem", id)
        session = DBSession()
        cpath = session.get(CanonicalPath, id)
        if cpath is None:
            raise KeyError(
                "The resource %r does not exist." % six.text_type(id))
        for obj in (*cpath.item.cpaths, cpath.item):
            session.delete(obj)

    def __getitem__(self, id):
        print("    getitem", id)
        # if id != self._prefix:
        #     import pdb; pdb.set_trace()
        session = DBSession()
        cpath = session.get(CanonicalPath, id)
        if cpath is None:
            raise KeyError(
                "The resource %r does not exist." % six.text_type(id))
        item = cpath.item
        properties = _convert_properties_from_dict(item.properties)
        # if id != self._prefix:
        #     import pdb; pdb.set_trace()
        resource_type = _get_resource_type(properties)
        content_type = properties.get(('getcontenttype', 'DAV:'))
        body = BytesIO(item.blob)
        path = item.path
        cid = self._prefix + path
        result = zeit.connector.resource.CachedResource(
            six.text_type(cid),
            self.DAVConnector._id_splitlast(cid)[1].rstrip('/'),
            resource_type,
            lambda: properties,
            lambda: body,
            content_type=content_type)
        # if id != self._prefix:
        #     import pdb; pdb.set_trace()
        return result

    def add(self, obj, verify_etag=True):
        print(f"    add {obj.id} {obj.contentType} {obj.type}")
        # if obj.id != self._prefix:
        #     import pdb; pdb.set_trace()
        path = self._id2path(obj.id)
        metadata = _convert_properties_to_dict(obj.properties)
        metadata.setdefault('DAV:', {}).setdefault('getcontenttype', obj.contentType)
        metadata.setdefault('DAV:', {}).setdefault('getlastmodified', datetime.datetime.now().strftime(RFC3339_FORMAT))
        metadata.setdefault(RESOURCE_TYPE_PROPERTY[1], {}).setdefault(RESOURCE_TYPE_PROPERTY[0], obj.type)
        if hasattr(obj.data, 'seek'):
            obj.data.seek(0)
        body = obj.data.read()
        session = DBSession()
        cpath = session.get(CanonicalPath, obj.id)
        if cpath is not None:
            print(f"    updated existing {obj.id} {obj.contentType} {obj.type}")
            # update existing item
            cpath.item.body = body
            cpath.item.properties.update(metadata)
            _remove_deleted_metadata(cpath.item.properties)
            return
        # we need to add a new item
        print(f"    new {obj.id} {obj.contentType} {obj.type}")
        session.add(StorageItem(
            path=path,
            blob=body,
            properties=metadata))
        session.add(CanonicalPath(id=obj.id, path=path))
        if obj.id.endswith('/'):
            cid = obj.id.rstrip('/')
        else:
            cid = obj.id + '/'
        if cid != obj.id:
            session.add(CanonicalPath(id=cid, path=path))
        (parent_id, child_id) = self.DAVConnector._id_splitlast(cid)
        if parent_id.endswith('://'):
            # the obj is the root
            return
        children = [x[0] for x in self.listCollection(parent_id)]
        parent_path = session.get(CanonicalPath, parent_id)
        if parent_path is None:
            import pdb; pdb.set_trace()
        print(f"    adding child {child_id} to {parent_id}")
        parent_path.item.blob = b'\n'.join(
            ('<td><a href="%s">%s</a></td>' % (x, x.rstrip('/'))).encode('utf-8')
            for x in sorted(set(children + [child_id])))

    def changeProperties(self, id, properties, locktoken=None):
        print(f"    changeProperties {id}")
        properties.pop(zeit.connector.interfaces.UUID_PROPERTY, None)
        metadata = _convert_properties_to_dict(properties)
        session = DBSession()
        cpath = session.get(CanonicalPath, id)
        cpath.item.properties.update(metadata)
        _remove_deleted_metadata(cpath.item.properties)

    def copy(self, old_id, new_id):
        import pdb; pdb.set_trace()

    def move(self, old_id, new_id):
        print(f"    move {old_id} {new_id}")
        session = DBSession()
        old_cpath = session.get(CanonicalPath, old_id)
        new_path = self._id2path(new_id)
        old_cpath.item.path = new_path
        for cpath in old_cpath.item.cpaths:
            if cpath.id == old_id + '/':
                cpath.id = new_id + '/'
                cpath.path = new_path
            elif cpath.id == old_id.rstrip('/'):
                cpath.id = new_id.rstrip('/')
                cpath.path = new_path
        (old_parent_id, old_child_id) = self.DAVConnector._id_splitlast(old_id)
        old_children = [x[0] for x in self.listCollection(old_parent_id)]
        old_parent_path = session.get(CanonicalPath, old_parent_id)
        print(f"    removing child {old_child_id} from {old_parent_id}")
        old_parent_path.item.blob = b'\n'.join(
            ('<td><a href="%s">%s</a></td>' % (x, x.rstrip('/'))).encode('utf-8')
            for x in sorted(set(x for x in old_children if x != old_child_id)))
        (new_parent_id, new_child_id) = self.DAVConnector._id_splitlast(new_id)
        new_children = [x[0] for x in self.listCollection(new_parent_id)]
        new_parent_path = session.get(CanonicalPath, new_parent_id)
        print(f"    adding child {new_child_id} to {new_parent_id}")
        new_parent_path.item.blob = b'\n'.join(
            ('<td><a href="%s">%s</a></td>' % (x, x.rstrip('/'))).encode('utf-8')
            for x in sorted(set(new_children + [new_child_id])))

    def lock(self, id, principal, until):
        # XXX does locking update getlastmodified DAV property?
        print("    lock", id, principal, until)
        session = DBSession()
        token = secrets.token_hex()
        session.add(Lock(
            path=self._id2path(id),
            principal=principal,
            until=until,
            token=token))
        return token

    def locked(self, id):
        session = DBSession()
        lock = session.get(Lock, self._id2path(id))
        if lock is None:
            result = (None, None, False)
            print("    locked", id, result)
            return result
        try:
            import zope.authentication.interfaces  # UI-only dependency
            authentication = zope.component.queryUtility(
                zope.authentication.interfaces.IAuthentication)
        except ImportError:
            authentication = None
        if authentication is not None:
            try:
                authentication.getPrincipal(lock.principal)
            except zope.authentication.interfaces.PrincipalLookupError:
                pass
            else:
                result = (lock.principal, lock.until, True)
                print("    locked", id, result)
                return result
        result = (lock.principal, lock.until, False)
        print("    locked", id, result)
        return result

    def unlock(self, id, locktoken=None, invalidate=True):
        print("    unlock", id, locktoken, invalidate)
        session = DBSession()
        lock = session.get(Lock, self._id2path(id))
        if lock is None:
            import pdb; pdb.set_trace()
        else:
            session.delete(lock)
        return lock.token

    @classmethod
    def factory(cls):
        import zope.app.appsetup.product
        print("    postgresql.Connector.factory")
        config = zope.app.appsetup.product.getProductConfiguration(
            'zeit.connector')
        return cls({
            'default': config['document-store'],
            'search': config['document-store-search']})


class TransactionBoundCachingConnector(Connector):
    pass


def connectorFactory():
    """Factory for creating the connector with data from zope.conf."""
    print("    postgresql.connectorFactory")
    import zope.app.appsetup.product
    config = zope.app.appsetup.product.getProductConfiguration(
        'zeit.connector')
    return Connector({
        'default': config['document-store'],
        'search': config['document-store-search']})


@zope.component.adapter(zeit.connector.interfaces.IResourceInvalidatedEvent)
def invalidate_cache(event):
    connector = zope.component.getUtility(
        zeit.connector.interfaces.IConnector)
    try:
        connector.invalidate_cache(event.id)
    except ValueError:
        # The connector isn't responsible for the id, or the id is just plain
        # invalid. There is nothing to invalidate then anyway.
        pass
