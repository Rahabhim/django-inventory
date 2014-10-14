# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2014
# Only a few rights reserved

import logging
from company.management.commands.misc import verbosity_levels, SyncCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

import json
import os
import os.path
from collections import Counter
from assets.models import Item
from common.models import Location
from company.models import Department
from movements.models import PurchaseOrder, Movement
from products.models import ItemTemplate

class Command(SyncCommand):
    help = 'Import Purchase Order from "reports" dump'

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.add_option('--cache-file', help="File to cache data in/out from")
        parser.add_option('--location-tmpl-id', type=int, help="Default location template to prefer")

        return parser

    def handle(self, *args, **options):
        self._pre_handle(*args, **options)
        logger = logging.getLogger('command')

        if len(args) != 1:
            raise CommandError("Must be called with a single argument, the JSON file")

        self._location_tmpl_id = options['location_tmpl_id']
        cache_data = {}
        fp = None
        cache_fname = None
        if options['cache_file']:
            cache_fname = os.path.expanduser(options['cache_file'])

        if cache_fname and os.path.exists(cache_fname):
            try:
                fp = open(cache_fname, 'rb')
                cache_data = json.load(fp)
            except Exception, e:
                logger.error("Could not read cache from %s: %s", cache_fname, e)
                return
            finally:
                if fp:
                    fp.close()
                fp = None

        try:
            fp = open(args[0], 'rb')
            json_data = json.load(fp)
        except Exception:
            logger.exception("Cannot load data from file: %s", args[0])
            raise CommandError("Could not load data")
        finally:
            if fp:
                fp.close()
            fp = None

        try:
            self.import_po(json_data, cache_data)
        except ValueError, e:
            logger.error(u"Could not import: %s", e)
        except Exception:
            logger.exception("Could not import:")

        if cache_fname and cache_data:
            try:
                fp = open(cache_fname, 'wb')
                json.dump(cache_data, fp, indent=2)
                fp.close()
            except Exception, e:
                logger.error("Could not read cache from %s: %s", cache_fname, e)
                return
        return

    def import_po(self, data, cache_data):
        logger = logging.getLogger('command.po_import')
        logger.debug("Importing %d entries from JSON: %s", data['count'], data['report_data'].get('title', ''))

        for field_id in ("src_contract.name", "item_template.description",
                        "location.department.name", "location.department.code",
                        "location.department.id", "serial_number"):
            if field_id not in data['report_data']['fields']:
                raise ValueError("Incorrect data, missing %s field" % field_id)


        for gr in data['groupped_results']:
            if gr['group_level'] == 0:
                continue
            logger.debug("Parsing group_level %d: %d values", gr['group_level'], len(gr['values']))

            if gr.get('group_by', [''])[-1] == 'src_contract.id':
                self._map_contracts(gr['values'], cache_data)
            elif gr.get('group_by', [''])[-1] == 'item_template.id':
                self._map_products(gr['values'], cache_data)
            elif not gr.get('group_by', False):
                if self.ask("Proceed with %d assets?", len(gr['values'])):
                    self._do_assets(gr['values'], cache_data)
            else:
                raise ValueError("Unknown 'group_by' in level %s: %r", gr['group_level'], gr['group_by'])

    def _map_contracts(self, values, cache_data):
        cache = cache_data.setdefault('contract2po', {})
        for val in values:
            remote_id = str(val['src_contract.id'])
            if remote_id in cache:
                continue
            if self._active != 'i':
                break
            print "Please enter PO #ID for remote source-contract #%s: %s" % (remote_id, val['src_contract.name'])
            purchase_order = None
            while True:
                print "?",
                r = raw_input()
                if not r:
                    continue
                if r.strip() == '-':
                    print "Stop"
                    break
                try:
                    purchase_order = PurchaseOrder.objects.get(pk=int(r.strip()))
                    if purchase_order.state == 'draft':
                        break
                    else:
                        print "Purchase Order #%d cannot be used, it is in %s state" % (purchase_order.id, purchase_order.state)
                        continue
                except ValueError, e:
                    print "Invalid input:", e
                except ObjectDoesNotExist:
                    print "No such PO"

            if purchase_order:
                cache[remote_id] = purchase_order.id

    def _map_products(self, values, cache_data):
        cache = cache_data.setdefault('product_map', {})
        for val in values:
            remote_id = str(val['item_template.id'])
            if remote_id in cache:
                continue
            print "Please enter product #ID for remote #%s: %s" % (remote_id, val['item_template.description'])
            found = ItemTemplate.objects.filter(description=val['item_template.description'])

            if self._active is True and len(found) == 1:
                item_template = found[0]
                cache[remote_id] = item_template.id
                continue
            elif self._active == 'i':
                pass
            else:
                # don't ask in non-interactive mode!
                break

            for p in found:
                print "    #%d [%s] %s" % (p.id, p.manufacturer.name, p.description)
            item_template = None
            while self._active == 'i':
                print "?",
                r = raw_input()
                if not r:
                    continue
                if r.strip() == '-':
                    print "Stop"
                    break
                if r.strip() == 'y' and len(found) == 1:
                    item_template = found[0]
                    break
                try:
                    item_template = ItemTemplate.objects.get(pk=int(r.strip()))
                    break
                except ValueError, e:
                    print "Invalid input:", e
                except ObjectDoesNotExist:
                    print "No such product"

            if item_template:
                cache[remote_id] = item_template.id

    def _do_assets(self, values, cache_data):
        logger = logging.getLogger('command.po_import.assets')
        contracts_map = {}
        product_map = {}

        lsrcs = Location.objects.filter(department__isnull=True, usage='procurement')[:1]
        if not lsrcs:
            logger.error('There is no procurement location configured in the system!')
            return

        for remote_id, local_id in cache_data.get('contract2po', {}).items():
            contracts_map[remote_id] = PurchaseOrder.objects.get(pk=local_id)

        for remote_id, local_id in cache_data.get('product_map', {}).items():
            product_map[remote_id] = ItemTemplate.objects.get(pk=local_id)

        logger.debug("Doing %d assets with %d products, %d contracts", len(values), len(product_map), len(contracts_map))

        last_line = cache_data.get('last_line', 0)
        line_num = 0
        for row in values:
            line_num += 1
            if last_line > line_num:
                continue
            if self._limit and (line_num - last_line) >= self._limit:
                break
            cache_data['last_line'] = line_num

            purchase_order = contracts_map[str(row['src_contract.id'])]
            product = product_map[str(row['item_template.id'])]

            location = self._get_location(row, cache_data)
            if not location:
                continue

            movement, c = Movement.objects.get_or_create(stype='in', state='draft',
                    location_src=lsrcs[0], location_dest=location,
                    purchase_order=purchase_order,
                    defaults=dict(create_user=purchase_order.create_user,
                                    date_act=purchase_order.issue_date, ))

            if c:
                movement.save()

            if row['serial_number'] and movement.items.filter(item_template=product, serial_number=row['serial_number']).exists():
                continue
            movement.items.create(item_template=product, serial_number=row['serial_number'])

        # fix product quantities in PO
        counter = Counter([ ( contracts_map[str(row['src_contract.id'])],
                                product_map[str(row['item_template.id'])]) \
                                for row in values])
        for sc_it, count in counter.items():
            purchase_order, product = sc_it
            line, c = purchase_order.items.get_or_create(item_template=product)
            if line.qty < count:
                line.qty = count
                line.save()

        return

    def _get_location(self, row, cache_data):
        cache = cache_data.setdefault('department_map', {})
        remote_id = str(row['location.department.id'])
        if remote_id in cache:
            dept = Department.objects.get(pk=cache[remote_id])
        else:
            for dept in Department.objects.filter(code=row['location.department.code']):
                if dept.name == row['location.department.name']:
                    break
                if self.ask("Map remote department #%s %s to local #%d %s?", remote_id,
                            row['location.department.name'], dept.id, dept.name):
                    break
            else:
                dept = False

            if (not dept) and self._active == 'i':
                print "Please enter Department ID for remote: #%s: %s\n#" % (remote_id, row['location.department.name']),
                while True:
                    r = raw_input()
                    if not r:
                        print "?",
                        continue
                    if r.strip() == '-':
                        print "Skip this line"
                        return False

                    try:
                        dept = Department.objects.get(pk=int(r.strip()))
                        if self.ask("Department found: #%d %s Are you sure?", dept.id, dept.name):
                            break
                        else:
                            dept = False
                    except ValueError, e:
                        print "Invalid input:", e
                    except ObjectDoesNotExist:
                        print "No such department"
            if not dept:
                raise ValueError("No department, stopping")

            cache[remote_id] = dept.id

        # now, try to find the default location:
        locations = []
        if self._location_tmpl_id:
            locations = dept.location_set.filter(active=True, template_id=int(self._location_tmpl_id))[:1]
        if not locations:
            locations = dept.location_set.filter(active=True)[:1]

        if (not locations) and self.ask("Department #%d %s has no locations, create from template?",
                                        dept.id, dept.name):
            dept.fix_locations()
            locations = dept.location_set.filter(active=True)[:1]
        if not locations:
            raise ValueError("Department #%d %s has no active locations!" % (dept.id, dept.name))
        return locations[0]

#eof
