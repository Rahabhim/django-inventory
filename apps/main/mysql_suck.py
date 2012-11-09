# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2012 P. Christeas <xrg@hellug.gr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, version 3 of the
#    License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#
##############################################################################

import logging
import os
import sys
import MySQLdb
import optparse
import weakref

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
import settings

try:
    import cPickle as pickle
    __hush_pyflakes = [pickle, ]
except ImportError:
    import pickle

BATCH_LIMIT=1000

def bq(ss):
    """Back-quote for MySQL """
    return '`' + ss + '`'

class DiscardRow(BaseException):
    """Stops column processing and discards single row data

        Similar to `GeneratorExit`, in a way
    """
    pass

def _get_model(mmodel):
    retm = None
    if isinstance(mmodel, basestring):
        app, nmodel = mmodel.split('.', 1)
        retm = models.get_model(app, nmodel)
        if not retm:
            raise AttributeError("Cannot find model: %s" % mmodel)
    else:
        retm = mmodel
    return retm

class MyS_Connector(object):
    """Take care of setup and connection to MySQL
    """
    _log = logging.getLogger('MySQL.connector')

    def __init__(self):
        self.myconn = None
        self._tables = {}
        self._fstore_path = None

    @staticmethod
    def add_mysql_options(parser, group_name="MySQL connection options"):
        """Utility to add MySQL connection options to OptionParser
        """
        assert isinstance(parser, optparse.OptionParser)

        pgroup = optparse.OptionGroup(parser, group_name)
        pgroup.add_option('--my-host', help="MySQL host")
        pgroup.add_option('--my-port', help="MySQL port")
        pgroup.add_option('--my-user', help="MySQL user")
        pgroup.add_option('--my-passwd', help="MySQL password")
        pgroup.add_option('--my-ask-passwd', action="store_true", default=False,
                    help="Ask for MySQL password on console")
        pgroup.add_option('--my-dbname', dest="my_db", help="MySQL database name")
        pgroup.add_option('--my-fstore', dest="my_fstore",
                    help="Path of persistent file storage")
        parser.add_option_group(pgroup)

    def connect(self, options, load=False):
        myconn_kwargs = {'charset': 'utf8'}
        for kw in ('host', 'port', 'user', 'passwd', 'db'):
            val = options.get('my_' + kw)
            if val:
                myconn_kwargs[kw] = val

        if options['my_ask_passwd']:
            import getpass
            myconn_kwargs['passwd'] = getpass.getpass("Enter MySQL password for %s@%s: " % \
                (myconn_kwargs['user'], myconn_kwargs.get('db','*')))

        if options['my_fstore']:
            self._fstore_path = os.path.expanduser(options['my_fstore'] % dict(dbname=settings.DATABASES['default']['SUCK']))

        self._log.info("Init. Connecting to MySQL db...")

        try:
            self.myconn = MySQLdb.connect(**myconn_kwargs)
            self._log.info("Connected.")
        except Exception, e:
            self._log.error("Failed to contact MySQL. %s", e)
            return False
        if load:
            self._load()
        for t in self._tables.values():
            t().init()
        return True

    def cursor(self):
        if not self.myconn:
            raise RuntimeError("You have to connect first")
        return self.myconn.cursor()

    def close(self, save=False):
        """Close the connection
        """
        if save:
            self._save()

        if self.myconn:
            self.myconn.close()
        self.myconn = None

    def _load(self):
        """Loads peristent data from pickle file

            Connector must have been connect()ed first
        """
        assert self._fstore_path, "You must connect() first"
        if not os.path.exists(self._fstore_path):
            self._log.info("File \"%s\" doesn't exist, not loading any data", self._fstore_path)
            return

        try:
            fp = open(self._fstore_path, 'rb')
            ldata = pickle.load(fp)
            fp.close()
            assert isinstance(ldata, dict), "Bad data: %s" % type(fp)
            for k, data in ldata.items():
                t = self._tables[k]
                if not t:
                    self._log.warning("Pickled data contained table %s, but now it doesn't exist!", k)
                    continue
                t()._table_data = data
            self._log.debug("Sucessfully loaded pickled data from \"%s\"", self._fstore_path)

        except EnvironmentError, e:
            self._log.warning("Could not load data from \"%s\": %e", self._fstore_path, e)
        except Exception, e:
            self._log.error("Error loading data from \"%s\":", self._fstore_path, exc_info=True)

    def _save(self):
        """ Saves persistent data into pickle file
        """
        assert self._fstore_path, "You must connect() first"
        ldata = {}
        for k, t in self._tables.items():
            ldata[k] = t()._table_data

        try:
            fp = open(self._fstore_path, 'wb')
            pickle.dump(ldata, fp)
            sys.stdout.write('S')
            sys.stdout.flush()
            self._log.debug("Sucessfully saved data into \"%s\"", self._fstore_path)

        except EnvironmentError, e:
            self._log.warning("Could not save data to \"%s\": %e", self._fstore_path, e)
        except Exception, e:
            self._log.error("Error saving data to \"%s\":", self._fstore_path, exc_info=True)

    def run_all(self, tables, limit=None, dry=False, **kwargs):
        """ Run algorithm for all (mentioned) tables

            @param tables a list of table names to use. Order matters
        """

        tobjs = []
        for tname in tables:
            if not tname in self._tables:
                raise KeyError("Table %s doesn't exist" % tname)
            t = self._tables[tname]
            tobjs.append(t())

        for t in tobjs:
            t.run(limit=limit, dry=dry, **kwargs)
            if limit is not None:
                if 'found' in t._stats:
                    limit -= t._stats['found']
                if limit <= 0:
                    break
        self._log.debug("Done with %d tables", len(tobjs))

class sColumn(object):
    def __init__(self, name):
        self._name = name
        self._myqindex = None

    def init(self, table):
        pass

    def makeMyQuery(self, query):
        query['cols'].append(self._name)
        self._myqindex = len(query['cols']) - 1

    def postProcess(self, qres, out, context=None):
        """Read one column of result data from qres, write into 'out' dict

            @param qres the tuple containing one row of SELECT data
            @param out a dictionary of values to feed into Django

            @raise DiscardRow if this row is already imported and all its
                data shall be discarded
        """

        raise NotImplementedError(self.__class__.__name__)

class Table_Suck(object):
    batch_limit = BATCH_LIMIT

    def __init__(self, table_name, orm_model, connector):
        self.table_name = table_name
        assert isinstance(connector, MyS_Connector), type(connector)
        self._connector = weakref.ref(connector)
        connector._tables[table_name] = weakref.ref(self)
        self._columns = []
        self._stats = dict() # TODO
        self._offset = 0
        self._after_handlers = []
        self._table_data = {}
        self._orm_model = orm_model
        self._django_model = None

    def __iadd__(self, column):
        assert isinstance(column, sColumn), column
        self._columns.append(column)
        return self

    def init(self):
        """ Late initialization of columns

            This must happen after connector._load(), because the dicts of
            _table_data must have settled first
        """
        self._django_model = _get_model(self._orm_model)
        for c in self._columns:
            c.init(self)

    def getQuery(self, limit=None):

        query = dict(cols=[], clause=[], args=[])
        for c in self._columns:
            c.makeMyQuery(query)

        qstr = 'SELECT %s FROM %s' % ( ', '.join(map(bq, query['cols'])), bq(self.table_name))
        if query['clause']:
            qstr += ' WHERE ' + (' AND '.join(query['clause']))
        if limit:
            qstr += ' LIMIT %d, %d' %(self._offset, limit)
        return qstr, query['args']

    def run(self, limit=None, dry=False, **kwargs):
        log = self._connector()._log
        log.debug("Running for table %s, limit=%s", self.table_name, limit)
        nfound = 0
        mycr = self._connector().cursor()
        while (not limit) or (nfound < limit):

            nlimit = self.batch_limit
            if limit and (limit - nfound < nlimit):
                nlimit = limit - nfound
            qry, args = self.getQuery(nlimit)
            log.debug("Query: %s ; %r", qry, args)
            mycr.execute(qry, args)
            if not mycr.rowcount:
                log.debug("No more results from %s", self.table_name)
                break
            log.debug("Got %d results", mycr.rowcount)
            self._offset += mycr.rowcount
            for rline in mycr:
                if limit and nfound >= limit:
                    break

                out = {}
                try:
                    for c in self._columns:
                        c.postProcess(rline, out)
                except DiscardRow:
                    # go on with next rline
                    continue
                log.debug("Out data: %r", out)
                nfound += 1
                if not dry:
                    r = self._push_data(out)
                    for ah in self._after_handlers:
                        ah(r, rline)
                sys.stdout.write('.')
                sys.stdout.flush()

            if self._connector()._fstore_path:
                # Just in case, we save at regular intervals
                self._connector()._save()

        log.debug("Finished table %s, %d results", self.table_name, nfound)
        self._stats['found'] = nfound

        return True

    def _push_data(self, odata):
        """Push the line of data into Django
        """
        r = self._django_model(**odata)
        r.save()
        return r

class IDmap_Column(sColumn):
    rtype = int

    def init(self, table):
        self._map_data = table._table_data.setdefault(self._name, {})
        table._after_handlers.append(self._get_result)

    def postProcess(self, qres, out, context=None):
        if qres[self._myqindex] in self._map_data:
            raise DiscardRow

    def _get_result(self, r, rline):
        """Keeps the result of orm.create() into map data
        """
        assert r, repr(r)
        self._map_data[rline[self._myqindex]] = r.id

class simple_column(sColumn):
    def __init__(self, name, oname):
        super(simple_column, self).__init__(name)
        self._oname = oname

    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        val = qres[self._myqindex]
        out[self._oname] = val

class Str_Column(simple_column):
    pass

class Int_Column(simple_column):
    pass

class Bool_Column(simple_column):
    pass

class Special_Column(sColumn):
    pass

class Date_Column(simple_column):
    """ Date (not time) column
    """
    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        val = qres[self._myqindex]
        if val is None:
            out[self._oname] = None
        else:
            out[self._oname] = val.strftime('%Y-%m-%d')

class Str_Column_Required(Str_Column):
    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        val = qres[self._myqindex]
        if not val:
            raise DiscardRow
        out[self._oname] = val

class Str_Column_Default(Str_Column):
    def __init__(self, name, oname, default="-"):
        Str_Column.__init__(self, name, oname)
        self._default = default

    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        val = qres[self._myqindex]
        if not val:
            val = self._default
        out[self._oname] = val

class Str_Column_NotNull(Str_Column):
    """ Str_Column, which will map "NULL" (string) to empty
    """
    def postProcess(self, qres, out, context=None):
        super(Str_Column_NotNull, self).postProcess(qres, out, context=context)
        if out[self._oname] == 'NULL':
            out[self._oname] = None

class Enum2Bool_Column(simple_column):
    """ Convert a 'Y'/ 'N' enum to pg. boolean

    """
    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        val = qres[self._myqindex]
        if val in ('Y', 'y'):
            out[self._oname] = True
        else:
            out[self._oname] = False

class Contain_Column(sColumn):
    """Column that creates a secondary entry for a subset of the data

        Example: Address inside a Partner table.
    """
    def __init__(self, oname):
        super(Contain_Column, self).__init__('')
        self._oname = oname
        self._columns = []

    def __iadd__(self, column):
        assert isinstance(column, sColumn), column
        self._columns.append(column)
        return self

    def init(self, table):
        table._after_handlers.append(self._push_cdata)
        for c in self._columns:
            c.init(table)

    def makeMyQuery(self, query):
        for c in self._columns:
            c.makeMyQuery(query)

    def postProcess(self, qres, out, context=None):
        pass

    def _push_cdata(self, r, rline):
        """prepare and push the data as a contained subset
        """
        sout = {}

        try:
            for c in self._columns:
                c.postProcess(rline, sout, context=None)

            getattr(r, self._oname).create(**sout)
        except DiscardRow:
            pass

class M2O_Column(sColumn):
    """Create a new sub-record for a many2one field

    """
    def __init__(self, oname, omodel):
        super(M2O_Column, self).__init__('')
        self._oname = oname
        self._omodel = omodel
        self._columns = []
        self._django_model = None

    def __iadd__(self, column):
        assert isinstance(column, sColumn), column
        self._columns.append(column)
        return self

    def init(self, table):
        for c in self._columns:
            c.init(table)

    def makeMyQuery(self, query):
        for c in self._columns:
            c.makeMyQuery(query)

    def postProcess(self, qres, out, context=None):
        """prepare the data as a contained subset
        """
        nout = {}

        if self._django_model is None:
            self._django_model = _get_model(self._omodel)

        try:
            for c in self._columns:
                c.postProcess(qres, nout, context=context)

            n = self._django_model(**nout)
            n.save()
            out[self._oname] = n.id
        except DiscardRow:
            pass

class Ref_Column(simple_column):
    """ Reference column, corresponding to many2one
    """
    def __init__(self, name, oname, otable, omodel=None, fast_mode=True):
        super(Ref_Column, self).__init__(name, oname,)
        self.otable = otable
        self._id_column = None
        self._omanager = None
        self._fast_mode = fast_mode
        if omodel:
            self._omanager = CachingPkSet(_get_model(omodel).objects)

    def init(self, table):
        """Try to keep a weakref of the other table
        """
        t = table._connector()._tables[self.otable]
        for c in t()._columns:
            if isinstance(c, IDmap_Column):
                self._id_column = weakref.ref(c)
                break
        else:
            raise KeyError("Cannnot find ID column in table %s" % self.otable)
        
        try:
            if not self._omanager:
                self._omanager = CachingPkSet(getattr(table._django_model, self._oname).field.rel.to.objects)
        except Exception, e:
            table._connector()._log.error("Cannot find related field %s.%s: %s", table.table_name, self._name, e)
            raise

    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        rid = qres[self._myqindex]
        if rid:
            mref = self._id_column()._map_data.get(rid, None)
            if mref is None:
                raise ValueError("Don't have id #%s in table %s for %s" % (rid, self.otable, self._name))
            if self._fast_mode:
                out[self._oname + '_id'] = mref
            else:
                out[self._oname] = self._omanager.get(pk=mref)
        else:
            out[self._oname] = None

class Ref_NN_Column(Ref_Column):
    """ Reference column, which only sets output if input is not null

        This is useful to create a COALESCE effect from 2 inputs into one field
    """

    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        rid = qres[self._myqindex]
        if not rid:
            return
        mref = self._id_column()._map_data.get(rid, None)
        if mref is None:
            raise ValueError("Don't have id #%d in table %s for %s" % (rid, self.otable, self._name))
        if self._fast_mode:
            out[self._oname + '_id'] = mref
        else:
            out[self._oname] = self._omanager.get(pk=mref)

class Static_Column(sColumn):
    """Column that pushes a constant value into every pg row
    """

    def __init__(self, value, oname):
        super(Static_Column, self).__init__('')
        self._value = value
        self._oname = oname

    def makeMyQuery(self, query):
        pass

    def postProcess(self, qres, out, context=None):
        out[self._oname] = self._value

class Static_Ref_Column(sColumn):
    """Looks up a value by expression, uses that in M2O fields
    """

    def __init__(self, expr, oname, model):
        super(Static_Ref_Column, self).__init__('')
        assert isinstance(expr, dict), type(expr)
        self._expr = expr
        self._model = model
        self._oname = oname
        self._value = None

    def makeMyQuery(self, query):
        pass

    def postProcess(self, qres, out, context=None):
        if self._value is None:
            proxy = _get_model(self._model)
            res, c = proxy.objects.get_or_create(**self._expr)
            self._value = res.id
        out[self._oname] = self._value

class Static_Ref2M_Column(Static_Ref_Column):
    """ Like static-ref, but for M2M records
    """

    def postProcess(self, qres, out, context=None):
        if self._value is None:
            proxy = _get_model(self._model)
            res = proxy.objects.filter(**self._expr)
            if res:
                self._value = [r.id for r in res ]
            else:
                self._value = []
        out[self._oname] = self._value

class StrLookup_Column(sColumn):
    """Convert a string column into a M2O looked-up value

        Say we have in mysql a set of records like::
            [ {'color': 'black',...}, {'color': 'red', ...}, {'color': 'black', ...}]

        and we want to map the 'color' column into a 'color_id' one in ORM,
        such that color_id.name will be 'black', 'red', etc.

        This column will implement the mapping.
    """

    def __init__(self, name, oname, bmodel, bname='name'):
        super(StrLookup_Column, self).__init__(name)
        self._oname = oname
        self._bmodel = bmodel
        self._bname = bname
        self._django_model = None

    def init(self, table):
        self._map_data = table._table_data.setdefault(self._name, {})

    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        val = qres[self._myqindex]
        if not val:
            return

        if val not in self._map_data:
            if self._django_model is None:
                self._django_model = _get_model(self._bmodel)

            expr = { self._bname: val }
            res = self._django_model.objects.filter(**expr)
            if res:
                self._map_data[val] = res[0].id
            else:
                res = self._django_model(**{self._bname: val})
                res.save()
                self._map_data[val] = res.id

        out[self._oname] = self._map_data[val]

    def _get_result(self, r, rline):
        """Keeps the result of orm.create() into map data
        """
        assert r, repr(r)
        self._map_data[rline[self._myqindex]] = r

class ParentName_Column(simple_column):
    """Looks up or creates the parent inherited record, based on name
    
        It could have been a `Str_Column`, on name, meaning that a parent
        object would always be created.
        But, when one already exists, we come up with an IntegrityError.
    """
    
    def __init__(self, name, oname, parent_column, parentname='name'):
        simple_column.__init__(self, name, oname)
        self._parent_column = parent_column
        self._parentname = parentname
        self._omanager = None

    def init(self, table):
        simple_column.init(self, table)
        try:
            self._omanager = weakref.ref(getattr(table._django_model, self._parent_column).field.rel.to.objects)
        except Exception, e:
            table._connector()._log.error("Cannot find related field %s.%s: %s", table.table_name, self._name, e)
            raise

    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        val = qres[self._myqindex]
        out[self._oname] = val
        try:
            exp = { self._parentname: val }
            rec = self._omanager().get(**exp)
            out[self._parent_column] = rec
        except ObjectDoesNotExist, e:
            pass

class Table_SuckToo(Table_Suck):
    """Variant of Table_Suck that can work on multiple SQL tables
    
        This one has a modified version of run(), able to handle more than one
        relations in the source SQL.
    """
    def __init__(self, *args, **kwargs):
        super(Table_SuckToo,self).__init__(*args, **kwargs)
        self._result_handlers = []

    def run(self, limit=None, dry=False, **kwargs):
        log = self._connector()._log
        log.debug("Running for table %s, limit=%s", self.table_name, limit)
        nfound = 0
        mycr = self._connector().cursor()
        while (not limit) or (nfound < limit):

            nlimit = self.batch_limit
            if limit and (limit - nfound < nlimit):
                nlimit = limit - nfound
            qry, args = self.getQuery(nlimit)
            log.debug("Query: %s ; %r", qry, args)
            mycr.execute(qry, args)
            if not mycr.rowcount:
                log.debug("No more results from %s", self.table_name)
                break
            log.debug("Got %d results", mycr.rowcount)
            results = [] # may hold quite some data
            self._offset += mycr.rowcount
            for rline in mycr:
                if limit and nfound >= limit:
                    break

                out = {}
                try:
                    for c in self._columns:
                        c.postProcess(rline, out)
                except DiscardRow:
                    # go on with next rline
                    if out:
                        raise RuntimeError("Non-empty out")
                    continue
                log.debug("Out data: %r", out)
                nfound += 1
                results.append((rline, out))
                sys.stdout.write('.')
                sys.stdout.flush()

            if not results:
                # all of the above had DiscardRow
                continue

            # we have to finish with previous query in `mycr` before
            # the result handlers can re-use the cursor. So, it's out
            # of the first loop
            if not dry:
                for rh in self._result_handlers:
                    rh(mycr, results)

                for rline, out in results:
                    r = False
                    if out.get('__skip_push', False):
                        if not isinstance(out['__skip_push'], bool):
                            r = out['__skip_push']
                        # but don't push anyway
                    else:
                        r = self._push_data(out)
                    if r is False:
                        continue
                    for ah in self._after_handlers:
                        ah(r, rline)

            if self._connector()._fstore_path:
                # Just in case, we save at regular intervals
                self._connector()._save()

        log.debug("Finished table %s, %d results", self.table_name, nfound)
        self._stats['found'] = nfound

        return True

class CachingPkSet(object):
    def __init__(self, queryset):
        self._cached_ids = {}
        self._queryset = queryset

    def get(self, pk):
        if pk not in self._cached_ids:
            # if len(self._cached_ids) > 1000:
            #    prune some cache...
            self._cached_ids[pk] = self._queryset.get(pk=pk)
        return self._cached_ids[pk]

#eof
