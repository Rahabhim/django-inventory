# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from main.conf import settings
from django.core.exceptions import ObjectDoesNotExist

import optparse
import logging
from main import mysql_suck as M

def custom_options(parser):
    M.MyS_Connector.add_mysql_options(parser)
    pgroup = optparse.OptionGroup(parser, "Iteration options")
    pgroup.add_option('--limit', type=int, help="Limit of forms to import"),
    pgroup.add_option('--dry-run', action="store_true", default=False,
                help="Don't change anything")
    pgroup.add_option('--slice', type=int,
                help="Slice of records to process at a time"),

class QPlaceholder(object):
    def __init__(self, other):
        self._id = id(other)

    def __eq__(self, other):
        return isinstance(other, QPlaceholder) and other._id == self._id

    def __repr__(self):
        return "<QPlaceholder for 0x%x>" % self._id

    def replace(self, alist, rep):
        return [ (self == a) and rep or a for a in alist]

class One2ManyColumn(M.sColumn):
    _log = logging.getLogger('MySQL.one2many')

    def __init__(self, name, oname, ktable, kcolumn):
        """
            @param name the local ID column
            @param oname key in `out` dict to store look-up data
            @param ktable the SQL table to lookup
            @param kcolumn column in ktable to match against this.name
        """
        super(One2ManyColumn,self).__init__(name)
        self._oname = oname
        self._ktable = ktable
        self._kcolumn = kcolumn
        self._columns = [ M.Str_Column(self._kcolumn, self._kcolumn),]

    def __iadd__(self, column):
        assert isinstance(column, M.sColumn), column
        self._columns.append(column)
        return self

    def init(self, table):
        assert isinstance(table, M.Table_SuckToo), table
        table._result_handlers.append(self._result_handler)
        for c in self._columns:
            c.init(table)
        self._qry, self._qargs = self.getQuery()
        self._log.debug("Query: %s ; %r", self._qry, self._qargs)

    def getQuery(self):
        query = dict(cols=[], clause=[M.bq(self._kcolumn) +' IN %s',], \
                args=[QPlaceholder(self),])
        for c in self._columns:
            c.makeMyQuery(query)

        qstr = 'SELECT %s FROM %s' % ( ', '.join(map(M.bq, query['cols'])), M.bq(self._ktable))
        qstr += ' WHERE ' + (' AND '.join(query['clause']))
        return qstr, query['args']

    def postProcess(self, qres, out, context=None):
        out[self._oname] = []
        out[self._oname+'+id'] = qres[self._myqindex]
    
    def _result_handler(self, cr, results):
        if not results:
            return
        lcol = self._oname + '+id'
        # Invert the results->out table. We want it indexed by its
        # id column (assume it's unique!)
        lres = {}
        for r, o in results:
            lres[o.pop(lcol)] = o
        # results[*][1] won't have any [self._oname+'+id'] item any more

        # now, we have a list of id columns to lookup, use it at the right
        # place of self._qargs
        args = QPlaceholder(self).replace(self._qargs, lres.keys())
        print self, args
        cr.execute(self._qry, args)
        for rline in cr:
            kout = {}
            try:
                for c in self._columns:
                    c.postProcess(rline, kout)
            except M.DiscardRow:
                # go on with next rline
                continue
            self._log.debug("Kout data: %r", kout)
            kid = kout[self._kcolumn]
            lres[kid][self._oname].append(kout)

        # now, what?

class KtimColumn(One2ManyColumn):
    _bundle_product = None
    def _get_bundle_product(self):
        if not self._bundle_product:
            product_obj = M._get_model('products.ItemTemplate')
            self._bundle_product = product_obj.objects.get(description=u'Σύνθεση')
        return self._bundle_product
    
    def _result_handler(self, cr, results):
        super(KtimColumn, self)._result_handler(cr, results)
        loc_obj = M._get_model('common.Location')
        itemgroup_obj = M._get_model('assets.ItemGroup')
        
        # and, now, use the values!
        for r, out in results:
            loc_dict = dict(department=out.pop('_department'), \
                            name=out.pop('_location_name'), usage='internal')
            
            try:
                location = loc_obj.objects.get(**loc_dict)
            except ObjectDoesNotExist:
                location = loc_obj(**loc_dict)
                location.save()
            out['location'] = location
            
            if not out['_bundle']:
                raise ValueError("Bundle id %s has no ktim entries!" % r['BUNDLE_ID'])
            elif len(out['_bundle']) == 1:
                bdl = out.pop('_bundle')[0]
                func_status = out.pop('_func_status')
                out.update(serial_number=bdl['serial_number'], item_template=bdl['item_template'])
                if bdl['property_number']:
                    out['property_number'] = str(bdl['property_number'])
                # TODO _agreed_price, _ar_timol, _seira_timol, _used, _date_invoiced, _date_received
                # _warranty, _contract
                if func_status:
                    pass # TODO
            else:
                # Real Bundle, have to put multiple items
                item = itemgroup_obj(item_template=self._get_bundle_product(), 
                        location=out['location'])
                item.save()
                for bdl in out.pop('_bundle'):
                    iout = dict(serial_number=bdl['serial_number'], is_bundled=True,
                            item_template=bdl['item_template'])
                    if bdl['property_number']:
                        iout['property_number'] = str(bdl['property_number'])
                    item.items.create(**iout)
                out['__skip_push'] = item

class Ref_Column_dafuq(M.Ref_Column):
    def postProcess(self, qres, out, context=None):
        assert self._myqindex is not None

        rid = qres[self._myqindex]
        if rid:
            mref = self._id_column()._map_data.get(rid, None)
            if mref is None:
                mref = self._id_column()._map_data.get(rid.upper(), None)
            if mref is None:
                raise ValueError("Don't have id #%s in table %s for %s" % (rid, self.otable, self._name))
            out[self._oname] = self._omanager().get(pk=mref)
        else:
            out[self._oname] = None

class Command(BaseCommand):
    args = '<table ...>'
    help = 'Imports table from old Ktim. database'
    _myc = None
    _tables = []

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        custom_options(parser)
        return parser

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.DEBUG)
        self._init_tables()

        for d in settings.defaults:
            if options.get(d, None) is None:
                options[d] = settings.defaults[d]

        if not self._myc.connect(options, load=True):
            self.stderr.write("Cannot connect to MySQL!\n")
            return
        self.stderr.write("Connected. Start of sync\n")

        try:
            self._myc.run_all( args or [
                'KT_03_EIDOS',
                'KT_08_KATASKEYASTHS',
                'KT_05_PROIONTA',
                'KT_14_ONTOTHTES',
                'KT_01_ANADOXOI',
                'KT_11_MANAGERS',
                'KT_16_ANATH_ARXH',
                'KT_18_ERGA',
                'KT_06_YPOERGA',
                'MONADES',
                ], **options)
            self._myc.close(save=True)
        except Exception, e:
            self.stderr.write("Exception: %s\n" % unicode(e).encode('utf-8'))
            raise
        return

    def _init_tables(self):
        self._myc = myc = M.MyS_Connector()
        
        anadoxoi = M.Table_Suck('KT_01_ANADOXOI', 'procurements.Delegate', myc)
        anadoxoi += M.IDmap_Column('ANADOXOS_ID')
        anadoxoi += M.ParentName_Column('ANADOXOS_DESCR', 'name', 'partner_ptr')
        anadoxoi += M.Str_Column('WEB', 'web')
        anadoxoi_addr = M.Contain_Column('address_set')
        anadoxoi += anadoxoi_addr
        anadoxoi_addr += M.Str_Column_Default('CONTACT_PERSON', 'name')
        anadoxoi_addr += M.Str_Column('TELEPHONE', 'phone1')
        anadoxoi_addr += M.Str_Column('CONTACT_TEL', 'phone2')

        # KT_02_BUNDLES
        bundles = M.Table_SuckToo('KT_02_BUNDLES', 'assets.Item', myc)
        bundles += M.IDmap_Column('BUNDLE_ID')
        bundles += Ref_Column_dafuq("GLUC", '_department', 'MONADES', 'company.Department')
        bundles += M.Str_Column_Default("ONT_DESCR", '_location_name', '-')
        bundles += M.Str_Column("FUNC_STATUS", '_func_status')
        bundles_ktim = KtimColumn('BUNDLE_ID', '_bundle', 'KT_07_KTHMATOLOGIO', 'BUNDLE_ID')
        bundles += bundles_ktim
        
        bundles_ktim += M.Str_Column('SERIAL_NO', 'serial_number')
        bundles_ktim += M.Str_Column("KOSTOS_EUR", '_agreed_price')
        bundles_ktim += M.Str_Column("AR_TIMOL", '_ar_timol')
        bundles_ktim += M.Str_Column("SEIRA_TIMOL", '_seira_timol')
        bundles_ktim += M.Str_Column("AR_KTHM", 'property_number')
        bundles_ktim += M.Str_Column("USED", '_used')
        bundles_ktim += M.Date_Column("DATE_PARALAVHS", '_date_received')
        bundles_ktim += M.Date_Column("DATE_TIMOL", '_date_invoiced')
        bundles_ktim += M.Str_Column("WARRANTY", '_warranty')
        bundles_ktim += M.Ref_Column("PROION_ID", 'item_template', 'KT_05_PROIONTA')
        bundles_ktim += M.Ref_Column("YPOERGO_ID", '_contract', 'KT_06_YPOERGA', 'procurements.Contract')

        product_cat = M.Table_Suck('KT_03_EIDOS', 'products.ItemCategory', myc)
        product_cat += M.IDmap_Column('EIDOS_ID')
        product_cat += M.Str_Column('EIDOS_DESCR', 'name')
        # product_cat += M.Bool_Column('IS_BUNDLE', 'is_bundle')
        #product_cat += M.Static_Ref_Column(dict(parent_id=False),
        #        'parent_id', 'products.ItemCategory') TODO


        products = M.Table_Suck('KT_05_PROIONTA', 'products.ItemTemplate', myc)
        products += M.IDmap_Column('PROION_ID')
        products += M.Str_Column('PROION_DESCR', 'description')
        products += M.Ref_Column('KATASK_ID', 'manufacturer', 'KT_08_KATASKEYASTHS')
        products += M.Ref_Column('EIDOS_ID', 'category', 'KT_03_EIDOS')
        # products += M.Static_Column('product', 'type')

        # KT_08_KATASKEYASTHS
        katask = M.Table_Suck('KT_08_KATASKEYASTHS', 'products.Manufacturer', myc)
        katask += M.IDmap_Column('KATASK_ID')
        katask += M.Str_Column('KATASK_DESCR', 'name')
        katask += M.Str_Column('WEB', 'web')

        # KT_11_MANAGERS
        managers = M.Table_Suck('KT_11_MANAGERS', 'company.Department', myc)
        managers += M.IDmap_Column('MANAGER_ID')
        managers += M.Str_Column('SHORT_DESCRIPTION', 'name')
        managers += M.Static_Ref_Column(dict(name=u'ΠΔΕ'), 'dept_type_id', 'company.DepartmentType')
        
        # All rest of columns are not set in old db, anyway...
        #managers += M.Str_Column('WEB', 'website')
        #managers += M.Str_Column('DESCRIPTION', 'description')
        #managers_addr = M.M2O_Column('address_id', 'res.partner.address')
        #managers += managers_addr
        #managers_addr += M.Str_Column_Required('CONTACT_PERSON', 'name')
        #managers_addr += M.Str_Column('TELEPHONE', 'phone')
        #managers_addr += M.Str_Column('CONTACT_TEL', 'mobile')

        # KT_14_ONTOTHTES
        onto = M.Table_Suck('KT_14_ONTOTHTES', 'common.LocationTemplate', myc)
        onto += M.IDmap_Column('ONT_TYPE_ID')
        onto += M.Str_Column('ONT_DESCR', 'name')

        # KT_16_ANATH_ARXH
        anath = M.Table_Suck('KT_16_ANATH_ARXH', 'company.Department', myc)
        anath += M.IDmap_Column('ANATHETOUSA_ARXH')
        anath += M.Str_Column('ARXH_DESCR', 'name')
        anath += M.Static_Ref_Column(dict(name=u'Αναθέτουσα αρχή'), 'dept_type_id', 'company.DepartmentType')
        
        #anath += M.Str_Column('WEB', 'website')
        #anath_addr = M.Contain_Column('common.Address', 'address')
        #anath += anath_addr
        #anath_addr += M.Str_Column('CONTACT_PERSON', 'name')
        #anath_addr += M.Str_Column('TELEPHONE', 'phone')
        #anath_addr += M.Str_Column('CONTACT_TEL', 'mobile')
        #anath += M.Static_Ref2M_Column([('id.ref', '=', 'ktimatologio.partner_cat_anath')],
        #        'category_id', 'res.partner.category')


        # KT_18_ERGA
        erga = M.Table_Suck('KT_18_ERGA', 'procurements.Project', myc)
        erga += M.IDmap_Column('ERGO_ID')
        erga += M.Str_Column('ERGO_DESCR', 'description')
        erga += M.Str_Column('ERGO_SHORT_DESCR', 'name')

        # KT_06_YPOERGA
        ypoerga = M.Table_Suck('KT_06_YPOERGA', 'procurements.Contract', myc)
        ypoerga += M.IDmap_Column('YPOERGO_ID')
        ypoerga += M.Str_Column('YPOERGO_DESCR', 'description')
        ypoerga += M.Str_Column('YPOERGO_SHORT_DESCR', 'name')
        ypoerga += M.Date_Column('DATE_SIGN', 'date_start')
        ypoerga += M.Date_Column('END_DATE', 'end_date')
        ypoerga += M.Str_Column('DIARKEIA_EGYHSHS', 'warranty_dur')
        ypoerga += M.Str_Column('XRONOS_APOKRISHS', 'service_response')
        ypoerga += M.Str_Column('XRONOS_APOKATASTASHS', 'repair_time')
        ypoerga += M.Str_Column('FILE_NAME', 'kp_filename')
        #ypoerga += M.Str_Column('TYPE_OF_ANATHETOUSA', 'kp_type')
        # FIXME: they should set "partner" from the subclass'es partner
        ypoerga += M.Ref_NN_Column('ANATH_FOREAS_ID', 'partner', 'KT_11_MANAGERS')
        ypoerga += M.Ref_NN_Column('ANATH_OTHER_ID', 'partner', 'KT_16_ANATH_ARXH')
        ypoerga += M.Ref_Column('ERGO_ID', 'parent', 'KT_18_ERGA')
        ypoerga += M.Ref_Column('ANADOXOS_ID', 'delegate', 'KT_01_ANADOXOI')

        # MONADES
        monades = M.Table_Suck('MONADES', 'company.Department', myc)
        monades += M.IDmap_Column('GLUC')
        monades += M.Str_Column('GLUC', 'code')
        monades += M.Str_Column('YPEPTH_ID', 'code2')
        monades += M.Str_Column('ONOMASIA', 'name')
        monades += M.StrLookup_Column('TYPOS_ONOMA', 'dept_type_id', 'company.DepartmentType')
        monades += M.Str_Column('DNSH_ONOMA', 'section_name')
        monades += M.Str_Column('OTA_ONOMA', 'ota_name')
        monades += M.Str_Column('NOM_ONOMA', 'nom_name')
        # TODO monades += M.XXX_Column('MANAGER_ID', '??') # foreas
        monades += M.Enum2Bool_Column('KATARGHSH', 'deprecate')
        monades += M.Ref_Column('SYGXONEYSH_GLUC', 'merge', 'MONADES')

        self._tables += [ onto, anadoxoi, product_cat, products, katask, anath,
                managers, erga, ypoerga, monades, bundles ]

#eof
