# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved


from django import forms

class Node(object):
    @classmethod
    def _key(cls, child):
        return child._obj.name

    def __init__(self):
        self._children = []

    def __eq__(self, other):
        return False

    def children(self):
        return self._children

    def add(self, child):
        inod = ItemNode(child)
        ck = self._key(inod)
        for i in xrange(len(self._children)):
            if self._key(self._children[i]) > ck:
                self._children.insert(i, inod)
                break
        else:
            self._children.append(inod)
        return inod

    def do_choices(self, field):
        ret = []
        for cc in self._children:
            ret.append(cc.do_choices(field))
        return ret

    def find(self, needle, parent_name='parent'):
        """Find a node among our children that references object `needle`

            The function is only allowed to touch `parent` of `needle`
        """
        if self == getattr(needle, parent_name):
            for c in self._children:
                if c == needle:
                    return c
        else:
            for c in self._children:
                ret = c.find(needle)
                if ret:
                    return ret
        return None

class RootNode(Node):
    def __init__(self, name):
        self._children = []
        self.name = name

    def __eq__(self, other):
        return other is None

    def consume_queryset(self, queryset, parent_name='parent'):
        pending_nodes = list(queryset)
        niter = 0
        nread = 0

        while pending_nodes:
            qlist = pending_nodes
            pending_nodes = []

            niter += 1
            for ic in qlist:
                nread += 1
                ic_parent = getattr(ic, parent_name)
                if ic_parent is None:
                    self.add(ic)
                elif ic_parent in pending_nodes:
                    pending_nodes.append(ic)
                else:
                    parent = self.find(ic_parent, parent_name=parent_name)
                    if parent:
                        parent.add(ic)
                    else:
                        pending_nodes.append(ic)
                        if ic.parent not in qlist:
                            pending_nodes.insert(0, ic_parent)
            if niter > 10:
                break

        if pending_nodes:
            raise RuntimeError
        return True

class ItemNode(Node):
    def __init__(self, obj, parent=None):
        super(ItemNode, self).__init__()
        self._obj = obj
        #self._parent = parent

    def do_choices(self, field):
        ret = (field.prepare_value(self._obj), field.label_from_instance(self._obj))
        if self._children:
            ret = [ ret[1], [ (ret[0], ret[1]), ]]
            for cc in self._children:
                ret[1].append(cc.do_choices(field))
        return ret

    def __eq__(self, other):
        #assert isinstance(other, ItemCategory), other
        return self._obj.id == other.id

class ModelTreeIterator(object):
    def __init__(self, field):
        self.field = field

    def __iter__(self):
        if not self.field.choice_cache:
            self.field._cache_compute()

        for choice in self.field.choice_cache:
            yield choice

    def __len__(self):
        if not self.field.choice_cache:
            self.field._cache_compute()
        return len(self.field.choice_cache)

class ModelTreeChoiceField(forms.ModelChoiceField):
    def __init__(self, parent_name, *args, **kwargs):
        self._parent_name = parent_name
        super(ModelTreeChoiceField, self).__init__(*args, **kwargs)

    def _cache_compute(self):
        self.choice_cache = []
        if self.empty_label is not None:
            self.choice_cache.append((u"", self.empty_label))

        the_root = RootNode(None)
        the_root.consume_queryset(self.queryset, parent_name=self._parent_name)

        self.choice_cache.extend(the_root.do_choices(self))

    def _get_choices(self):
        assert self.queryset is not None, "No queryset"
        return ModelTreeIterator(self)

    choices = property(_get_choices, forms.ChoiceField._set_choices)

    #forms.ModelChoiceField

#eof