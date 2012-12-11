# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from company.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import threading

import optparse
import logging
import datetime

ADMIN_USER = 1

verbosity_levels = { '0': logging.ERROR, '1': logging.WARNING, '2': logging.INFO, '3': logging.DEBUG}

"""
    Available commands:
    
    --ping      Test connection with LDAP server
    --all       Sync all departments, again, with LDAP
    --incr      (default) Incremental sync
    
    
"""

class Command(BaseCommand):
    args = '<table ...>'
    help = 'Synchronizes with LDAP server'

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        pgroup = optparse.OptionGroup(parser, "LDAP commands")
        pgroup.add_option("--ping", action="store_true", default=False,
                    help="Test connection with LDAP server")
        
        pgroup = optparse.OptionGroup(parser, "Iteration options")
        pgroup.add_option('--limit', type=int, help="Limit of forms to import")
        pgroup.add_option('--dry-run', action="store_true", default=False,
                    help="Don't change anything")
        #pgroup.add_option('--slice', type=int,
        #            help="Slice of records to process at a time"),
        return parser

    
    def handle(self, *args, **options):
        self._lconn = None
        self._logger = logging.getLogger('command')
        import ldap
        v = options.get('verbosity', None)
        if v:
            self._logger.setLevel(verbosity_levels.get(v, logging.INFO))
        try:
            self._open()
            if options['ping']:
                self.cmd_ping()
            else:
                raise NotImplementedError
                pass
        except ldap.LDAPError, e:
            edir = e.args[0]
            self._logger.error("LDAP error: %s", edir['desc'])
            if 'info' in edir:
                self._logger.error("LDAP error info: %s", edir['info'])
            
        except Exception:
            self._logger.exception("Exception:")
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
        import ldap

        l = ldap.open(defs['host'], defs.get('port',389))
        l.protocol_version = ldap.VERSION3
        l.simple_bind_s(defs['user_dn'], defs.get('passwd', ''))
        self._lconn = l

#eof
