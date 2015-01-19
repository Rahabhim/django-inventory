# -*- encoding: utf-8 -*-
import random

class ReplicasRouter(object):
    """A router that sets up a simple master/slave configuration"""
    
    def __init__(self):
        import settings # lazy
        self.dbs = {}
        for db_alias, vals in settings.DATABASES.items():
            if '-' in db_alias:
                cluster, db = db_alias.split('-', 1)
                self.dbs.setdefault(cluster, {})[db_alias] = vals.get('ROUTED_MODELS', [])

        self.system_apps = getattr(settings, 'DATABASE_NON_ROUTED_APPS', [])

    def db_for_read(self, model, **hints):
        """Point all read operations to a random read slave"""
        dbt = self.dbs.get(hints.get('cluster', 'read'), {'default': [] })
        if model._meta.app_label in self.system_apps:
            dbt = dbt.copy() # will receive dbs explicitly allowed to route this system model

            model_tag = '%s.%s' %( model._meta.app_label, model._meta.object_name)
            for dbname in dbt.keys():
                if model_tag not in dbt[dbname]:
                    del dbt[dbname]
            if not dbt:
                return None
        if len(dbt) > 1:
            return random.choice(dbt.keys()[1:])
        else:
            return dbt.keys()[0]

    def db_for_write(self, model, **hints):
        "Point all write operations to the master"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        "Allow any relation between two objects in the db pool"
        db1 = obj1._state.db
        db2 = obj2._state.db
        if db1 == 'default' and db2 == 'default':
            return True
        elif db2 == 'default':
            # swap
            db2 = db1
            db1 = 'default'
        
        if db1 == 'default':
            for dbs in self.dbs.values():
                if db2 in dbs:
                    return True
            return None
        else:
            # both dbs must be in the same cluster
            for dbs in self.dbs.values():
                if db1 in dbs:
                    return db2 in dbs
        return None

    def allow_syncdb(self, db, model):
        "Explicitly put all models on all databases."
        return True

#eof