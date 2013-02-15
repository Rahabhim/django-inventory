# -*- encoding: utf-8 -*-
import logging
import optparse
from django.core.management.base import BaseCommand, CommandError
from company.conf import settings

verbosity_levels = { 0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}


def ustr(ss):
    if isinstance(ss, unicode):
        return ss
    else:
        return ss.decode('utf-8')

def utf8(ss):
    if isinstance(ss, unicode):
        return ss.encode('utf-8')
    else:
        return ss

class SyncCommand(BaseCommand):
    def create_parser(self, prog_name, subcommand):
        parser = super(SyncCommand, self).create_parser(prog_name, subcommand)
        pgroup = optparse.OptionGroup(parser, "Iteration options")
        pgroup.add_option('--limit', type=int, help="Limit of forms to import")
        pgroup.add_option('--dry-run', action="store_false", dest="active",
                    help="Don't change anything (default)")
        pgroup.add_option('--active', action="store_true", dest="active",
                    help="Save all changes without asking")
        pgroup.add_option("--interactive", action="store_true", default=False,
                    help="Interactive ask about each change")
        #pgroup.add_option('--slice', type=int,
        #            help="Slice of records to process at a time"),
        return parser

    def _pre_handle(self, *args, **options):
        self._logger = logging.getLogger('command')
        v = options.get('verbosity', None)
        self._answered = {}
        if v:
            self._verbose = int(v)
            self._logger.setLevel(verbosity_levels.get(self._verbose, logging.INFO))
        if options['active'] is False:
            self._active = False
        elif options['interactive']:
            self._active = 'i'
        elif options['active'] is True:
            self._active = True
        else:
            self._logger.info("No --active or --interactive options given, defaulting to dry-run")
            self._active = False

        self._limit = int(options['limit'] or 10)

    def ask(self, question, *args):
        if self._active is True:
            return True
        elif self._active == 'i':
            if args:
                prompt = question % args
            else:
                prompt = question

            if question in self._answered:
                answer = self._answered[question]
                print prompt, " < %s" % ( answer and 'yes' or 'no')
                return answer
            while True:
                print prompt, # this handles unicode better than raw_input
                print '(y,n,a,d)',
                r = raw_input()
                if not r:
                    return False
                if r.lower() in ('y', 'yes'):
                    return True
                elif r.lower() in ('n', 'no'):
                    return False
                elif r.lower() in ('a', 'all'):
                    self._answered[question] = True
                    return True
                elif r.lower() in ('d', 'deny'):
                    self._answered[question] = False
                    return False
        else:
            self._logger.debug(question+ ' No', *args)
        return False

# --------------- LDAP part --------------

def _print_ldap_result(result):
    """ For debugging
    """
    for dn, attrs in result:
        print "DN: %s" % dn
        for key, val in attrs.items():
            print "    %s: %s" %( key, ','.join(map(ustr, val)))

def _add_ldap(ext_dn, base_dn):
    """Append base_dn to ext_dn
    """
    if ext_dn.endswith(','):
        return ext_dn + base_dn
    else:
        return ext_dn

def _subtract_dn(full_dn, base_dn):
    """Remove `base_dn` from `full_dn`
    """
    if full_dn.endswith(base_dn):
        return full_dn[:-len(base_dn)]
    else:
        return full_dn

def bind_ldap():
    """ Bind to LDAP, using settings from "company" app
    """
    defs = settings.ldap
    import ldap

    l = ldap.ldapobject.ReconnectLDAPObject(defs['uri'], trace_stack_limit=10)
    l.protocol_version = ldap.VERSION3
    if defs.get('tls', False):
        l.start_tls_s()
    l.simple_bind_s(defs['user_dn'], defs.get('passwd', ''))
    return l
#eof