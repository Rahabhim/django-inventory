# -*- encoding: utf-8 -*-
from company.conf import settings
from django.core.exceptions import ObjectDoesNotExist

import optparse
import datetime

from company.models import Department
ADMIN_USER = 1

from misc import SyncCommand, CommandError, ustr, utf8, \
        bind_ldap, _print_ldap_result, _add_ldap, _subtract_dn

"""
    Available commands:

    --ping      Test connection with LDAP server
    --all       Sync all departments, again, with LDAP
    --incr      (default) Incremental sync


"""

class Command(SyncCommand):
    args = '<code> ...'
    help = 'Synchronizes with LDAP server'

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        pgroup = optparse.OptionGroup(parser, "LDAP commands")
        pgroup.add_option("--ping", action="store_true", default=False,
                    help="Test connection with LDAP server")

        #pgroup.add_option('--slice', type=int,
        #            help="Slice of records to process at a time"),
        return parser


    def handle(self, *args, **options):

        import ldap
        self._lconn = None
        self._pre_handle(*args, **options)
        try:
            self._open()
            if options['ping']:
                self.cmd_ping()
            elif args:
                self.cmd_verify_depts(args)
            else:
                self.cmd_verify_incr()
        except ldap.CONNECT_ERROR:
            self._logger.exception("LDAP connect error:")
        except ldap.ADMINLIMIT_EXCEEDED, e:
            self._logger.error("LDAP admin limit exceeded: %s", e)
        except ldap.LDAPError, e:
            edir = e.args[0]
            self._logger.error("LDAP error: %s", edir['desc'])
            if 'info' in edir:
                self._logger.error("LDAP error info: %s", edir['info'])

        except Exception:
            self._logger.exception("Exception:")
        except KeyboardInterrupt:
            print
            pass
        finally:
            if self._lconn:
                try:
                    self._lconn.unbind()
                except Exception:
                    self._logger.debug("Error at unbind():", exc_info=True)
                self._lconn = None
        return


    def cmd_ping(self):
        """Open a connection and test remote server
        """
        self._logger.info("LDAP: I am %s", self._lconn.whoami_s())

    def _open(self):
        defs = settings.ldap
        self._lconn = bind_ldap()
        self._ou_base = defs.get('ou_base', '')

    def cmd_verify_depts(self, args):
        log = self._logger
        for gluc in args:
            log.debug("operating on: %s", gluc)
            try:
                dept = Department.objects.get(code=gluc)
            except ObjectDoesNotExist:
                log.warning("Department with code \"%s\" not found in our db!", gluc)
                continue

            log.debug("Found dept #%d %s [%s] : %s", dept.id, dept.code, dept.code2, dept.name)
            self._verify_dept(dept)

    def cmd_verify_incr(self):
        for dept in Department.objects.filter(ldap_dn__isnull=True)[:self._limit]:
            self._logger.debug("At dept #%d %s [%s] : %s", dept.id, dept.code, dept.code2, dept.name)
            self._verify_dept(dept)

    def _verify_dept(self, dept):
        import ldap
        import ldap.filter
        log = self._logger
        attrlist = ['cn', 'title', 'description']
        ou_filter = '(&(gsnUnitCode=%s)(objectClass=gsnUnit))'
        if True:
            if dept.ldap_dn and not dept.ldap_dn.startswith(('!','?')):
                log.debug("    this was \"%s\" in LDAP at %s", dept.ldap_dn, dept.ldap_mtime)
                # try to read the entry
                result = self._lconn.search_s(_add_ldap(dept.ldap_dn, self._ou_base), \
                            scope=ldap.SCOPE_BASE, attrlist=attrlist)
                if self._verbose >= 3:
                    _print_ldap_result(result)

                self._verify_name(dept, result[0])
                return
            elif not dept.code:
                log.debug("    no code, skipping...")
                return
            else:
                log.debug("    not associated with LDAP, searching by code...")

            if True:
                filterstr = ldap.filter.filter_format(ou_filter, (utf8(dept.code),))
                log.debug("Search under \"%s\" for: %s", self._ou_base, filterstr )
                result = self._lconn.search_s(self._ou_base, filterstr=filterstr, \
                            scope=ldap.SCOPE_SUBTREE, attrlist=attrlist)
                if self._verbose >= 3:
                    _print_ldap_result(result)
                if not result:
                    log.info("Department #%s %s [%s] not found in LDAP. %s", dept.id, dept.code, dept.code2, dept.name)
                    if self._active is True and not dept.ldap_dn:
                        dept.ldap_dn = '?'
                        dept.save()
                elif len(result) > 1:
                    log.warning("Multiple DNs (%d) found for unit #%s. Cannot associate",
                            len(result), dept.code)
                    for dn, attrs in result:
                        log.debug("    DN found: %s", dn)
                else:
                    dn, attrs = result[0]
                    part_dn = _subtract_dn(dn, self._ou_base)
                    log.debug("Found DN=%s for department #%s %s [%s]", part_dn, dept.id, dept.code, dept.code2)
                    question = "Do you want to associate dept #%s \"%s\" with DN=%s ?"
                    if not self._verify_name(dept, result[0]):
                        # question must be different so that ask() won't store the same default
                        question = "Do you still want to associate dept #%s \"%s\" with DN=%s ?"
                    if self.ask(question, dept.id, dept.name, part_dn):
                        dept.ldap_dn = part_dn
                        dept.ldap_mtime = datetime.datetime.now()
                        dept.save()

            #log.debug("End of unit")

    def _verify_name(self, dept, lres):
        lname = lres[1].get('description', None)
        if lname:
            assert len(lname) == 1, repr(lname)
            lname = ustr(lname[0])
        if dept.name == lname:
            return True
        else:
            self._logger.info("Department #%d has different name in our db compared to LDAP:\n\tHere: %s\n\tLDAP: %s",
                    dept.id, dept.name, lname or '<null>')
            return False
        # then, do nothing about that
#eof
