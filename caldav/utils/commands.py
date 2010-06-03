#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from lxml import etree
import uuid

from caldav.objects import Principal, Calendar, Event
from caldav.utils.namespace import ns, nsmap
from caldav.utils.url import glue


def children(client, parent, type = None):
    """
    List children, using a propfind (resourcetype) on the parent object,
    at depth = 1.
    TODO: There should be a better way.
    """
    c = []

    response = properties(client, parent, [("D", "resourcetype"),], 1)
    for path in response.keys():
        if path != parent.url.path:
            resource_type = response[path][ns("D", 'resourcetype')]
            cls = Event
            if resource_type is not None \
               and resource_type == ns("D", "collection"):
                cls = Calendar

            if resource_type == type or type is None:
                c.append(cls(client, url = parent.geturl(path), 
                             parent = parent))

    return c


def properties(client, object, props = [], depth = 0):
    """
    Find the properies `props` of object `object` and its children at
    maximum `depth` levels. (0 means only `object`).
    """
    rc = {}

    body = ""
    # build the propfind request
    if len(props) > 0:
        root = etree.Element("propfind", nsmap = nsmap)
        prop = etree.SubElement(root, ns("D", "prop"))
        for p in props:
            prop.append(etree.Element(ns(*p)))
        body = etree.tostring(root, encoding="utf-8", xml_declaration=True)

    response = client.propfind(object.url.path, body, depth)
    # All items should be in a <D:response> element
    for r in response.tree.findall(ns("D", "response")):
        href = r.find(ns("D", "href")).text
        rc[href] = {}
        for p in props:
            t = r.find(".//" + ns(*p))
            if t.text is None:
                val = t.find(".//*")
                if val is not None:
                    val = val.tag
                else:
                    val = None
            else:
                val = t.text
            rc[href][ns(*p)] = val

    return rc


def date_search(client, calendar, start, end = None):
    """
    Perform a time-interval search in the `calendar`.
    """
    rc = []

    dates = {"start": start}
    if end is not None:
        dates['end'] = end
    
    # build the request
    root = etree.Element(ns("C", "calendar-query"), nsmap = nsmap)
    prop = etree.SubElement(root, ns("D", "prop"))
    cdata = etree.SubElement(prop, ns("C", "calendar-data"))
    expand = etree.SubElement(cdata, ns("C", "expand"), **dates)
    filter = etree.SubElement(root, ns("C", "filter"))
    fcal = etree.SubElement(filter, ns("C", "comp-filter"), name = "VCALENDAR")
    fevt = etree.SubElement(fcal, ns("C", "comp-filter"), name = "VEVENT")
    etree.SubElement(fevt, ns("C", "time-range"), **dates)

    q = etree.tostring(root, encoding="utf-8", xml_declaration=True)
    response = client.report(calendar.url.path, q, 1)
    for r in response.tree.findall(".//" + ns("D", "response")):
        href = r.find(ns("D", "href")).text
        data = r.find(".//" + ns("C", "calendar-data")).text
        rc.append(Event(client, url = calendar.geturl(href), 
                        data = data, parent = object))

    return rc

def create_calendar(client, parent, name, id = None):
    """
    Create a new calendar with display name `name` in `parent`.
    """
    url = None
    if id is None:
        id = str(uuid.uuid1())

    root = etree.Element(ns("D", "mkcol"), nsmap = nsmap)
    set = etree.SubElement(root, ns("D", "set"))
    prop = etree.SubElement(set, ns("D", "prop"))
    type = etree.SubElement(prop, ns("D", "resourcetype"))
    coll = etree.SubElement(prop, ns("D", "collection"))
    calc = etree.SubElement(coll, ns("C", "calendar-collection"))
    dname = etree.SubElement(prop, ns("D", "displayname"))
    dname.text = name

    q = etree.tostring(root, encoding="utf-8", xml_declaration=True)
    path = glue(parent.url.path, id)

    r = client.mkcol(path, q)
    if r.status == 201:
        url = parent.geturl(path)

    return url

def create_event(client, calendar, data, id = None):
    url = None
    if id is None:
        id = str(uuid.uuid1())

    path = glue(calendar.url.path, id + ".ics")
    r = client.put(path, data)
    if r.status == 201:
        url = calendar.geturl(path)

    return url
