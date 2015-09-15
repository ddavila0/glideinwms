import os
from xml.dom.minidom import parse

ENTRY_INDENT = 6
ENTRY_DIR = 'entries.d'

class XmlElement(object):
    def __init__(self, xml):
        self.xml = xml
        self.children = []

    def get_child(self, tag):
        child = None
        for c in self.children:
            if c.xml.tagName == tag:
                child = c
                break
        return child

    def get_child_list(self, tag):
        child = self.get_child(tag)
        if child is None:
            return None
        return child.children

    def find(self, tag):
        found = []
        self._find(tag, found)
        return found

    def _find(self, tag, found):
        for c in self.children:
            if c.xml.tagName == tag:
                found.append(c)
            c._find(tag, found)

class XmlAttrElement(XmlElement):
    def extract_attr_val(self):
        if (not self.xml.getAttribute(u'type') in ("string","int","expr")):
            raise RuntimeError, "Wrong attribute type '%s', must be either 'int' or 'string'"%self.xml.getAttribute(u'type')

        if self.xml.getAttribute(u'type') in ("string","expr"):
            return str(self.xml.getAttribute(u'value'))
        else:
            return int(self.xml.getAttribute(u'value'))

class XmlFileElement(XmlElement):
    # this function converts a file element to the expected dictionary used in
    # cgWParamDict.add_file_unparsed()
    def to_dict(self):
        file_dict = {}
        if self.xml.hasAttribute(u'absfname'):
            file_dict[u'absfname'] = self.xml.getAttribute(u'absfname')
        else:
            file_dict[u'absfname'] = None
        if self.xml.hasAttribute(u'after_entry'):
            file_dict[u'after_entry'] = self.xml.getAttribute(u'after_entry')
        if self.xml.hasAttribute(u'const'):
            file_dict[u'const'] = self.xml.getAttribute(u'const')
        else:
            file_dict[u'const'] = u'False'
        if self.xml.hasAttribute(u'executable'):
            file_dict[u'executable'] = self.xml.getAttribute(u'executable')
        else:
            file_dict[u'executable'] = u'False'
        if self.xml.hasAttribute(u'relfname'):
            file_dict[u'relfname'] = self.xml.getAttribute(u'relfname')
        else:
            file_dict[u'relfname'] = None
        if self.xml.hasAttribute(u'untar'):
            file_dict[u'untar'] = self.xml.getAttribute(u'untar')
        else:
            file_dict[u'untar'] = u'False'
        if self.xml.hasAttribute(u'wrapper'):
            file_dict[u'wrapper'] = self.xml.getAttribute(u'wrapper')
        else:
            file_dict[u'wrapper'] = u'False'
        uopts = self.get_child(u'untar_options')
        if uopts is not None:
            uopt_dict = {}
            if uopts.xml.hasAttribute(u'absdir_outattr'):
                uopt_dict[u'absdir_outattr'] = uopts.xml.getAttribute(u'absdir_outattr')
            else:
                uopt_dict[u'absdir_outattr'] = None
            if uopts.xml.hasAttribute(u'dir'):
                uopt_dict[u'dir'] = uopts.xml.getAttribute(u'dir')
            else:
                uopt_dict[u'dir'] = None
            uopt_dict[u'cond_attr'] = uopts.xml.getAttribute(u'cond_attr')
            file_dict[u'untar_options'] = uopt_dict

        return file_dict

class XmlEntry(XmlElement):
    pass

class FactoryXmlConfig(XmlElement):
    def __init__(self, file):
        super(FactoryXmlConfig, self).__init__(None)
        self.file = file
        self.dom = None

        # cached variables to minimize dom accesses for better performance
        # these are looked up for each and every entry on reconfig
        self.submit_dir = None
        self.stage_dir = None
        self.monitor_dir = None
        self.log_dir = None
        self.client_log_dirs = None
        self.client_proxy_dirs = None

    def parse(self):
        d1 = parse(self.file)
        entry_dir_path = os.path.join(os.path.dirname(self.file), ENTRY_DIR)
        if os.path.exists(entry_dir_path):
            entries = d1.getElementsByTagName(u'entry')

            found_entries = {}
            for e in entries:
                found_entries[e.getAttribute(u'name')] = e

            files = sorted(os.listdir(entry_dir_path))
            for f in files:
                if f.endswith('.xml'):
                    d2 = parse(os.path.join(entry_dir_path, f))
                    merge_entries(d1, d2, found_entries)
                    d2.unlink()

        self.dom = d1
        self.xml = d1.documentElement
        build_tree(self)

    def unlink(self):
        self.dom.unlink()

    #######################
    #
    # FactoryXmlConfig getter functions
    #
    ######################
    def get_web_url(self):
        return os.path.join(self.get_child(u'stage').xml.getAttribute(u'web_base_url'),
            u"glidein_%s" % self.xml.getAttribute(u'glidein_name'))

    def get_submit_dir(self):
        if self.submit_dir == None:
            self.submit_dir = os.path.join(self.get_child(u'submit').xml.getAttribute(u'base_dir'),
                u"glidein_%s" % self.xml.getAttribute(u'glidein_name'))
        return self.submit_dir

    def get_stage_dir(self):
        if self.stage_dir == None:
            self.stage_dir = os.path.join(self.get_child(u'stage').xml.getAttribute(u'base_dir'),
                u"glidein_%s" % self.xml.getAttribute(u'glidein_name'))
        return self.stage_dir

    def get_monitor_dir(self):
        if self.monitor_dir == None:
            self.monitor_dir = os.path.join(self.get_child(u'monitor').xml.getAttribute(u'base_dir'),
                u"glidein_%s" % self.xml.getAttribute(u'glidein_name'))
        return self.monitor_dir

    def get_log_dir(self):
        if self.log_dir == None:
            self.log_dir  = os.path.join(self.get_child(u'submit').xml.getAttribute(u'base_log_dir'),
                u"glidein_%s" % self.xml.getAttribute(u'glidein_name'))
        return self.log_dir

    def get_client_log_dirs(self):
        if self.client_log_dirs == None:
            self.client_log_dirs = {}
            client_dir = self.get_child(u'submit').xml.getAttribute(u'base_client_log_dir')
            glidein_name = self.xml.getAttribute(u'glidein_name')
            for sc in self.get_child(u'security').find(u'security_class'):
                self.client_log_dirs[sc.xml.getAttribute(u'username')] = os.path.join(client_dir,
                    u"user_%s" % sc.xml.getAttribute(u'username'), u"glidein_%s" % glidein_name)

        return self.client_log_dirs

    def get_client_proxy_dirs(self):
        if self.client_proxy_dirs == None:
            self.client_proxy_dirs = {}
            client_dir = self.get_child(u'submit').xml.getAttribute(u'base_client_proxies_dir')
            glidein_name = self.xml.getAttribute(u'glidein_name')
            for sc in self.get_child(u'security').find(u'security_class'):
                self.client_proxy_dirs[sc.xml.getAttribute(u'username')] = os.path.join(client_dir,
                    u"user_%s" % sc.xml.getAttribute(u'username'), u"glidein_%s" % glidein_name)

        return self.client_proxy_dirs


#######################
#
# Utility functions
#
######################

def merge_entries(d1, d2, found_entries):
    entries1 = d1.getElementsByTagName(u'entries')[0]
    entries2 = d2.getElementsByTagName(u'entries')[0]

    for e in entries2.getElementsByTagName(u'entry'):
        entry_name = e.getAttribute(u'name')
        entry_clone = d1.importNode(e, True)
        if entry_name in found_entries:
            entries1.replaceChild(entry_clone, found_entries[entry_name])
        else:
            line_break = d1.createTextNode(u'\n%*s' % (ENTRY_INDENT,' '))
            entries1.insertBefore(line_break, entries1.lastChild)
            entries1.insertBefore(entry_clone, entries1.lastChild)
            found_entries[entry_name] = entry_clone

def build_tree(element):
    for c in element.xml.childNodes:
        if c.nodeType == c.ELEMENT_NODE:
            if c.tagName == u'attribute':
                element.children.append(XmlAttrElement(c)) 
            elif c.tagName == u'file':
                element.children.append(XmlFileElement(c)) 
            elif c.tagName == u'entry':
                element.children.append(XmlEntry(c))
            else:
                element.children.append(XmlElement(c))

            build_tree(element.children[-1])
