import os
from io import StringIO
import tempfile
import itertools
import filecmp
import difflib
import html
import pprint
from fontTools.ufoLib import fontInfoAttributesVersion3
import drawBot as bot

# ---------
# Directory
# ---------

def diffDirectories(
        root1,
        root2,
        ignorePaths1=None,
        ignorePaths2=None,
        onlyCompareFontDefaultLayers=True,
        normalizeFontContours=True,
        normalizeFontComponents=True,
        normalizeFontAnchors=True,
        normalizeFontGuidelines=True
    ):
    # gather from first root
    if ignorePaths1 is None:
        ignorePaths1 = []
    paths1 = _gatherFiles(root1, ignorePaths1)
    paths1 = [
        os.path.relpath(path, root1)
        for path in paths1
        if os.path.basename(path) != ".DS_Store"
    ]
    # gather from second root
    if ignorePaths2 is None:
        ignorePaths2 = []
    paths2 = _gatherFiles(root2, ignorePaths2)
    paths2 = [
        os.path.relpath(path, root2)
        for path in paths2
        if os.path.basename(path) != ".DS_Store"
    ]
    # look for existance differences
    added = []
    removed = []
    common = []
    allPaths = set(paths1) | set(paths2)
    for path in sorted(allPaths):
        if path in paths1 and path not in paths2:
            removed.append(path)
        elif path not in paths1 and path in paths2:
            added.append(path)
        else:
            common.append(path)
    # look for differences
    changed = {}
    for path in common:
        path1 = os.path.join(root1, path)
        path2 = os.path.join(root2, path)
        different, details = diffFile(
            path1,
            path2,
            onlyCompareFontDefaultLayers=onlyCompareFontDefaultLayers,
            normalizeFontContours=normalizeFontContours,
            normalizeFontComponents=normalizeFontComponents,
            normalizeFontAnchors=normalizeFontAnchors,
            normalizeFontGuidelines=normalizeFontGuidelines
        )
        if different:
            changed[path] = details
    # compile and return
    differences = dict(
        root1=root1,
        root2=root2,
        added=added,
        removed=removed,
        changed=changed
    )
    return differences

def _gatherFiles(directory, ignore):
    found = []
    if directory in ignore:
        return found
    for fileName in os.listdir(directory):
        path = os.path.join(directory, fileName)
        if path in ignore:
            continue
        if os.path.isdir(path):
            if os.path.splitext(path)[-1].lower() == ".ufo":
                found.append(path)
            else:
                found += _gatherFiles(path, ignore)
        else:
            found.append(path)
    return found

# ----
# File
# ----

def diffFile(
        path1,
        path2,
        onlyCompareFontDefaultLayers=True,
        normalizeFontContours=True,
        normalizeFontComponents=True,
        normalizeFontAnchors=True,
        normalizeFontGuidelines=True
    ):
    different = False
    fileType = os.path.splitext(path1)[-1].lower()
    if fileType in (".ufo", ".ufoz"):
        fileType = "UFO"
    details = dict(fileType=fileType, differences=None)
    if fileType == "UFO":
        font1 = OpenFont(path1, showInterface=False)
        font2 = OpenFont(path2, showInterface=False)
        different, differences = diffFont(
            font1,
            font2,
            onlyCompareDefaultLayers=onlyCompareFontDefaultLayers,
            normalizeContours=normalizeFontContours,
            normalizeComponents=normalizeFontComponents,
            normalizeAnchors=normalizeFontAnchors,
            normalizeGuidelines=normalizeFontGuidelines
        )
        details["differences"] = differences
    else:
        different = not filecmp.cmp(path1, path2)
    return different, details

# ----
# Font
# ----

def diffFont(
        font1,
        font2,
        glifVendor1=None,
        glifVendor2=None,
        onlyCompareDefaultLayers=True,
        normalizeContours=True,
        normalizeComponents=True,
        normalizeAnchors=True,
        normalizeGuidelines=True
    ):
    if glifVendor1 is None:
        glifVendor1 = makeGLIFVendorFromLayers(font1)
    if glifVendor2 is None:
        glifVendor2 = makeGLIFVendorFromLayers(font2)
    # basic attributes
    differences = diffObject(
        font1,
        font2,
        ("glyphOrder", "layerOrder")
    )
    # info
    info = diffInfo(font1.info, font2.info)
    if info:
        differences["info"] = info
    # groups
    groups = diffGroups(font1.groups, font2.groups)
    if groups:
        differences["groups"] = groups
    # kerning
    kerning = diffKerning(font1.kerning, font2.kerning)
    if kerning:
        differences["kerning"] = kerning
    # features
    features = diffFeatures(font1.features, font2.features)
    if features:
        differences["features"] = features
    # guidelines
    guidelines = diffGuidelines(font1, font2, normalize=normalizeGuidelines)
    if guidelines:
        differences["guidelines"] = guidelines
    # lib
    ignore = [
        "public.glyphOrder",
        "org.unifiedfontobject.normalizer.modTimes"
    ]
    lib = diffLib(font1.lib, font2.lib, ignore)
    if lib:
        differences["lib"] = lib
    # layers
    layers = diffLayers(
        font1,
        font2,
        glifVendor1=glifVendor1,
        glifVendor2=glifVendor2,
        onlyCompareDefaultLayers=onlyCompareDefaultLayers,
        normalizeContours=normalizeContours,
        normalizeComponents=normalizeComponents,
        normalizeAnchors=normalizeAnchors,
        normalizeGuidelines=normalizeGuidelines
    )
    if layers:
        differences["layers"] = layers
    different = bool(differences)
    return different, differences

def makeGLIFVendorFromLayers(font):
    # XXX
    # this uses private stuff in defcon.
    try:
        import defcon
    except ImportError:
        return {}
    vendor = {}
    if hasattr(font, "naked") and isinstance(font.naked(), defcon.Font):
        for layer in font.layers:
            nakedLayer = layer.naked()
            glyphSet = nakedLayer._glyphSet
            if glyphSet is None:
                continue
            layerName = layer.name
            for glyphName in layer.keys():
                # if the glyph object is already loaded,
                # don't get the GLIF because the object
                # is considered to be the truth.
                if glyphName in nakedLayer._glyphs:
                    pass
                else:
                    glif = glyphSet.getGLIF(glyphName)
                    vendor[layerName, glyphName] = glif
    return vendor

# ----
# Info
# ----

def diffInfo(info1, info2):
    attributes = list(fontInfoAttributesVersion3)
    attributes.remove("guidelines")
    differences = diffObject(
        info1,
        info2,
        attributes
    )
    if differences:
        differences["info1"] = info1
        differences["info2"] = info2
    return differences

# --------
# Features
# --------

def diffFeatures(features1, features2):
    # basic attributes
    differences = diffObject(
        features1,
        features2,
        ("text",)
    )
    if differences:
        differences["features1"] = features1
        differences["features2"] = features2
    return differences

# ------
# Groups
# ------

def diffGroups(groups1, groups2):
    differences = diffDict(groups1, groups2)
    if differences:
        differences["groups1"] = groups1
        differences["groups2"] = groups2
    return differences

# -------
# Kerning
# -------

def diffKerning(kerning1, kerning2):
    differences = diffDict(kerning1, kerning2)
    if differences:
        differences["kerning1"] = kerning1
        differences["kerning2"] = kerning2
    return differences

# ---
# Lib
# ---

def diffLib(lib1, lib2, ignore=None):
    differences = diffDict(lib1, lib2, ignore)
    if differences:
        differences["lib1"] = lib1
        differences["lib2"] = lib2
    return differences

# ------
# Layers
# ------

def diffLayers(
        font1,
        font2,
        glifVendor1=None,
        glifVendor2=None,
        onlyCompareDefaultLayers=True,
        normalizeContours=True,
        normalizeComponents=True,
        normalizeAnchors=True,
        normalizeGuidelines=True
    ):
    if glifVendor1 is None:
        glifVendor1 = {}
    if glifVendor2 is None:
        glifVendor2 = {}
    differences = dict(changed={})
    # name
    defaultLayer1 = font1.defaultLayer
    defaultLayerName1 = defaultLayer1.name
    defaultLayer2 = font2.defaultLayer
    defaultLayerName2 = defaultLayer2.name
    if defaultLayerName1 != defaultLayerName2:
        differences["defaultLayer"] = (defaultLayerName1, defaultLayerName2)
    # contents
    layerDifferences = diffLayer(
        defaultLayer1,
        defaultLayer2,
        glifVendor1=glifVendor1,
        glifVendor2=glifVendor2,
        normalizeContours=normalizeContours,
        normalizeComponents=normalizeComponents,
        normalizeAnchors=normalizeAnchors,
        normalizeGuidelines=normalizeGuidelines
    )
    if layerDifferences:
        differences["changed"][None] = layerDifferences
    if not onlyCompareDefaultLayers:
        layerNames1 = set([layerName for layerName in font1.layerOrder if layerName != font1.defaultLayer.name])
        layerNames2 = set([layerName for layerName in font2.layerOrder if layerName != font2.defaultLayer.name])
        added = layerNames2 - layerNames1
        if added:
            differences["added"] = {layerName : font2.getLayer(layerName) for layerName in added}
        removed = layerNames1 - layerNames2
        if removed:
            differences["removed"] = {layerName : font1.getLayer(layerName) for layerName in removed}
        common = layerNames1 & layerNames2
        changed = []
        for name in common:
            layer1 = font1.getLayer(name)
            layer2 = font2.getLayer(name)
            layerDifferences = diffLayer(
                layer1,
                layer2,
                glifVendor1=glifVendor1,
                glifVendor2=glifVendor2,
                normalizeContours=normalizeContours,
                normalizeComponents=normalizeComponents,
                normalizeAnchors=normalizeAnchors,
                normalizeGuidelines=normalizeGuidelines
            )
            if layerDifferences:
                differences["changed"][name] = layerDifferences
    if not differences["changed"]:
        del differences["changed"]
    return differences

# -----
# Layer
# -----

def diffLayer(
        layer1,
        layer2,
        glifVendor1=None,
        glifVendor2=None,
        normalizeContours=True,
        normalizeComponents=True,
        normalizeAnchors=True,
        normalizeGuidelines=True
    ):
    if glifVendor1 is None:
        glifVendor1 = {}
    if glifVendor2 is None:
        glifVendor2 = {}
    # basic attributes
    differences = diffObject(
        layer1,
        layer2,
        ("name", "color")
    )
    # lib
    ignore = [
        "org.unifiedfontobject.normalizer.modTimes"
    ]
    lib = diffLib(layer1.lib, layer2.lib, ignore)
    if lib:
        differences["lib"] = lib
    # glyphs
    glyphsDifferences = dict(changed={})
    glyphNames1 = set(layer1.keys())
    glyphNames2 = set(layer2.keys())
    added = glyphNames2 - glyphNames1
    if added:
        glyphsDifferences["added"] = list(sorted(added))
    removed = glyphNames1 - glyphNames2
    if removed:
        glyphsDifferences["removed"] = list(sorted(removed))
    common = glyphNames1 & glyphNames2
    for glyphName in common:
        needGlyphObjects = False
        glif1 = glifVendor1.get((layer1.name, glyphName))
        glif2 = glifVendor2.get((layer2.name, glyphName))
        if glif1 is None:
            needGlyphObjects = True
        elif glif2 is None:
            needGlyphObjects = True
        elif glif1 != glif2:
            needGlyphObjects = True
        if needGlyphObjects:
            glyph1 = layer1[glyphName]
            glyph2 = layer2[glyphName]
            glyphDifferences = diffGlyph(
                glyph1, glyph2,
                normalizeContours=normalizeContours,
                normalizeComponents=normalizeComponents,
                normalizeAnchors=normalizeAnchors,
                normalizeGuidelines=normalizeGuidelines
            )
            if glyphDifferences:
                glyphsDifferences["changed"][glyphName] = glyphDifferences
    if not glyphsDifferences["changed"]:
        del glyphsDifferences["changed"]
    if glyphsDifferences:
        differences["glyphs"] = glyphsDifferences
    if differences:
        differences["layer1"] = layer1
        differences["layer2"] = layer2
    return differences

def _getGlyphOrder(font):
    glyphOrder = list(font.glyphOrder)
    for layerName in font.layerOrder:
        layer = font.getLayer(layerName)
        for glyphName in sorted(layer.keys()):
            if glyphName not in glyphOrder:
                glyphOrder.append(glyphName)
    return glyphOrder

# -----
# Glyph
# -----

def diffGlyph(
        glyph1,
        glyph2,
        normalizeContours=True,
        normalizeComponents=True,
        normalizeAnchors=True,
        normalizeGuidelines=True
    ):
    # basic attributes
    differences = diffObject(
        glyph1,
        glyph2,
        ("unicodes", "width", "height", "note", "markColor")
    )
    # contours
    contours = diffContours(glyph1, glyph2, normalize=normalizeContours)
    if contours:
        differences["contours"] = contours
    # components
    components = diffComponents(glyph1, glyph2, normalize=normalizeComponents)
    if components:
        differences["components"] = components
    # anchors
    anchors = diffAnchors(glyph1, glyph2, normalize=normalizeAnchors)
    if anchors:
        differences["anchors"] = anchors
    # guidelines
    guidelines = diffGuidelines(glyph1, glyph2, normalize=normalizeGuidelines)
    if guidelines:
        differences["guidelines"] = guidelines
    # image
    image = diffImage(glyph1.image, glyph2.image)
    if image:
        differences["image"] = image
    # lib
    ignore = [
        "public.markColor"
    ]
    lib = diffLib(glyph1.lib, glyph2.lib, ignore)
    if lib:
        differences["lib"] = lib
    if differences:
        differences["glyph1"] = glyph1
        differences["glyph2"] = glyph2
    return differences

# --------
# Contours
# --------

def diffContours(glyph1, glyph2, normalize=True):
    contours1 = [contour for contour in glyph1.contours]
    contours2 = [contour for contour in glyph2.contours]
    if normalize:
        contours1, contours2 = matchObjectsWithAttributes(
            contours1,
            contours2,
            ("identifier",),
            (">len segments", "area")
        )
    pairs = itertools.zip_longest(contours1, contours2)
    added = []
    removed = []
    changed = []
    for contour1, contour2 in pairs:
        if contour1 is None:
            added.append(contour2)
        elif contour2 is None:
            removed.append(contour1)
        else:
            contourDifferences = diffContour(contour1, contour2, normalize=normalize)
            if contourDifferences:
                changed.append(contourDifferences)
    differences = {}
    if added:
        differences["added"] = added
    if removed:
        differences["removed"] = removed
    if changed:
        differences["changed"] = changed
    return differences

# -------
# Contour
# -------

def diffContour(contour1, contour2, normalize=True):
    # basic attributes
    differences = diffObject(
        contour1,
        contour2,
        ("identifier", "index", "clockwise")
    )
    # normalize
    original1 = contour1
    original2 = contour2
    if normalize:
        contour1, contour2 = _normalizeContours(contour1, contour2)
    # compare points
    points1 = [_pointData(point) for point in contour1.points]
    points2 = [_pointData(point) for point in contour2.points]
    added = []
    removed = []
    changed = []
    pairs = itertools.zip_longest(points1, points2)
    for point1, point2 in pairs:
        if point1 is None:
            added.append(point2["object"])
        elif point2 is None:
            removed.append(point1["object"])
        else:
            pointDifferences = {}
            for attr in point1.keys():
                if attr == "object":
                    continue
                value1 = point1[attr]
                value2 = point2[attr]
                if value1 != value2:
                    pointDifferences[attr] = dict(value1=value1, value2=value2)
            if pointDifferences:
                pointDifferences["point1"] = point1["object"]
                pointDifferences["point2"] = point2["object"]
                changed.append(pointDifferences)
    pointDifferences = {}
    if added:
        pointDifferences["added"] = added
    if removed:
        pointDifferences["removed"] = removed
    if changed:
        pointDifferences["changed"] = changed
    if pointDifferences:
        differences["points"] = pointDifferences
    # store the contours
    if differences:
        differences["contour1"] = original1
        differences["contour2"] = original2
    return differences

def _normalizeContours(contour1, contour2):
    contour1 = contour1.copy()
    contour2 = contour2.copy()
    if contour1.open or contour2.open:
        pass
    else:
        # set a consistent direction
        if contour1.clockwise != contour2.clockwise:
            contour2.clockwise = contour1.clockwise
        # find a start segment based on identifiers
        identifiers1 = {
            segment.onCurve.identifier : index
            for index, segment in enumerate(contour1)
            if segment.onCurve.identifier is not None
        }
        if identifiers1:
            for segment in contour2:
                identifier = segment.onCurve.identifier
                index = identifiers1.get(identifier)
                if index is not None:
                    contour2.setStartSegment(index)
                    break
        # guess the start segment
        else:
            contour1.autoStartSegment()
            contour2.autoStartSegment()
    return contour1, contour2

def _pointData(point):
    data = dict(
        object=point,
        name=point.name,
        identifier=point.identifier,
        x=point.x,
        y=point.y,
        type=point.type,
        smooth=point.smooth,
    )
    return data

# ---------
# Component
# ---------

def diffComponents(glyph1, glyph2, normalize=True):
    components1 = [component for component in glyph1.components]
    components2 = [component for component in glyph2.components]
    if normalize:
        components1, components2 = matchObjectsWithAttributes(
            components1,
            components2,
            ("identifier", "baseGlyph"),
            ("transformation", "baseGlyph")
        )
    differences = diffObjects(
        components1,
        components2,
        ("baseGlyph", "transformation", "identifier"),
        "component"
    )
    return differences

# ------
# Anchor
# ------

def diffAnchors(glyph1, glyph2, normalize=True):
    anchors1 = [anchor for anchor in glyph1.anchors]
    anchors2 = [anchor for anchor in glyph2.anchors]
    if normalize:
        anchors1, anchors2 = matchObjectsWithAttributes(
            anchors1,
            anchors2,
            ("identifier", "name", "color"),
            ("x", "y")
        )
    differences = diffObjects(
        anchors1,
        anchors2,
        ("name", "color", "x", "y", "identifier"),
        "anchor"
    )
    return differences

# ----------
# Guidelines
# ----------

def diffGuidelines(object1, object2, normalize=True):
    guidelines1 = [guideline for guideline in object1.guidelines]
    guidelines2 = [guideline for guideline in object2.guidelines]
    if normalize:
        guidelines1, guidelines2 = matchObjectsWithAttributes(
            guidelines1,
            guidelines2,
            # XXX
            # defcon is allowing "" as a name, but the
            # fontParts normalizer raises an error for
            # that name. so, cheat by going to the naked.
            ("identifier", ">naked name", "color"),
            ("angle", "x", "y")
        )
    differences = diffObjects(
        guidelines1,
        guidelines2,
        (">naked name", "color", "angle", "x", "y", "identifier"),
        "guideline"
    )
    return differences

# -----
# Image
# -----

def diffImage(image1, image2):
    differences = diffObject(
        image1,
        image2,
        ("data", "transformation")
    )
    if differences:
        differences["image1"] = image1
        differences["image2"] = image2
    return differences

# -------
# Pairing
# -------

def matchObjectsWithAttributes(objects1, objects2, matchAttributes, sortAttributes):
    matched1 = []
    matched2 = []
    unmatched1 = objects1
    unmatched2 = objects2
    for attr in matchAttributes:
        m1, m2, unmatched1, unmatched2 = pairObjectsWithAttribute(unmatched1, unmatched2, attr)
        matched1 += m1
        matched2 += m2
        if not unmatched1 and not unmatched2:
            break
    if unmatched1:
        matched1 += sortObjectsWithAttributes(unmatched1, sortAttributes)
    if unmatched2:
        matched2 += sortObjectsWithAttributes(unmatched2, sortAttributes)
    return matched1, matched2

def pairObjectsWithAttribute(objects1, objects2, attr):
    matches = {}
    for index, objects in ((0, objects1), (1, objects2)):
        for obj in objects:
            value = _fancyGetAttr(obj, attr)
            if value not in matches:
                matches[value] = ([], [])
            matches[value][index].append(obj)
    matched1 = []
    matched2 = []
    unmatched1 = []
    unmatched2 = []
    for objects in matches.values():
        pairs = itertools.zip_longest(objects[0], objects[1])
        for object1, object2 in pairs:
            if object1 is None:
                unmatched2.append(object2)
            elif object2 is None:
                unmatched1.append(object1)
            else:
                matched1.append(object1)
                matched2.append(object2)
    return matched1, matched2, unmatched1, unmatched2

def sortObjectsWithAttributes(objects, attributes):
    sorter = []
    for index, obj in enumerate(objects):
        sortable = []
        for attr in attributes:
            value = _fancyGetAttr(obj, attr)
            sortable.append(value)
        sortable.append(index)
        sorter.append(tuple(sortable))
    result = []
    for data in sorted(sorter):
        index = data[-1]
        result.append(objects[index])
    return result

def _fancyGetAttr(obj, attr):
    if attr.startswith(">len"):
        if " " in attr:
            attr = attr.split(" ")[-1]
            value = len(getattr(obj, attr))
        else:
            value = len(obj)
    elif attr.startswith(">naked"):
        attr = attr.split(" ")[-1]
        value = getattr(obj.naked(), attr)
    else:
        value = getattr(obj, attr)
    return value

# ---------
# Comparing
# ---------

def diffObjects(
        objects1, objects2,
        compareAttributes,
        objectTypeTag
    ):
    added = []
    removed = []
    changed = []
    pairs = itertools.zip_longest(objects1, objects2)
    for object1, object2 in pairs:
        if object1 is None:
            added.append(object2)
        elif object2 is None:
            removed.append(object1)
        else:
            d = diffObject(object1, object2, compareAttributes)
            if d:
                d[objectTypeTag + "1"] = object1
                d[objectTypeTag + "2"] = object2
                changed.append(d)
    differences = {}
    if added:
        differences["added"] = added
    if removed:
        differences["removed"] = removed
    if changed:
        differences["changed"] = changed
    return differences

def diffObject(object1, object2, attributes):
    differences = {}
    for attr in attributes:
        value1 = _fancyGetAttr(object1, attr)
        value2 = _fancyGetAttr(object2, attr)
        if value1 != value2:
            differences[attr] = dict(value1=value1, value2=value2)
    return differences

def diffDict(dict1, dict2, ignore=None):
    if ignore is None:
        ignore = []
    ignore = set(ignore)
    keys1 = set(dict1.keys()) - ignore
    keys2 = set(dict2.keys()) - ignore
    added = list(sorted(keys2 - keys1))
    removed = list(sorted(keys1 - keys2))
    common = keys1 & keys2
    changed = {}
    for key in common:
        value1 = dict1[key]
        value2 = dict2[key]
        if value1 != value2:
            changed[key] = dict(value1=value1, value2=value2)
    differences = {}
    if added:
        differences["added"] = added
    if removed:
        differences["removed"] = removed
    if changed:
        differences["changed"] = changed
    return differences

# ------
# Output
# ------

from xml.etree import cElementTree as ET

# HTML
# ----

def makeRootReport(differences):
    container = makeHTMLElement()
    body = container.find("body")
    reportRootDifferences(differences, body)
    return makeHTMLString(container)

def makeFontReport(differences):
    pass

# Contents

def reportRootDifferences(differences, body):
    container = ET.SubElement(body, "div", {"class" : "root"})
    root1 = differences["root1"]
    root2 = differences["root2"]
    reportRootPaths(root1, root2, container)
    if "removed" in differences:
        reportRemovedFiles(root1, root2, differences["removed"], container)
    if "added" in differences:
        reportAddedFiles(root1, root2, differences["added"], container)
    if "changed" in differences:
        reportChangedFiles(root1, root2, differences["changed"], container)

def reportRootPaths(root1, root2, parent):
    h1 = ET.SubElement(parent, "h1")
    h1.text = "Roots"
    diffs = [
        ("removed", root1),
        ("added", root2)
    ]
    makeDiffTable(diffs, parent)

def reportRemovedFiles(root1, root2, removed, parent):
    h1 = ET.SubElement(parent, "h1")
    h1.text = "Removed Files"
    diffs = []
    for path in removed:
        diffs.append(("removed", path))
    makeDiffTable(diffs, parent)

def reportAddedFiles(root1, root2, added, parent):
    h1 = ET.SubElement(parent, "h1")
    h1.text = "Added Files"
    diffs = []
    for path in added:
        diffs.append(("added", path))
    makeDiffTable(diffs, parent)

def reportChangedFiles(root1, root2, changed, parent):
    h1 = ET.SubElement(parent, "h1")
    h1.text = "Changed Files"
    container = ET.SubElement(parent, "div", {"class" : "changed"})
    fonts = []
    for path, data in changed.items():
        if data["fileType"] == "UFO":
            fonts.append((path, data))
        else:
            reportChangedFileGeneric(root1, root2, path, data, container)
    for path, data in fonts:
        reportChangedFont(path, data["differences"], container)

def reportChangedFileGeneric(root1, root2, path, differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "file"})
    h1 = ET.SubElement(container, "h1")
    h1.text = path
    p1 = os.path.join(root1, path)
    p2 = os.path.join(root2, path)
    try:
        f = open(p1, "r")
        text1 = f.read()
        f.close()
        f = open(p2, "r")
        text2 = f.read()
        f.close()
        reportChangedText(text1, text2, container)
    except UnicodeDecodeError:
        h2 = ET.SubElement(container, "h2", {"class" : "binaryFileWarning"})
        h2.text = "Unable to visualize binary file differences."

def reportChangedText(text1, text2, parent):
    rawDiffs = difflib.ndiff(text1.splitlines(), text2.splitlines())
    diffs = []
    for line in rawDiffs:
        token = line[:2].strip()
        line = line[2:]
        if token:
            if token in "+-":
                if token == "-":
                    action = "removed"
                else:
                    action = "added"
                diffs.append((action, line))
            else:
                continue
    makeDiffTable(diffs, parent)

def reportChangedFont(path, differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "file"})
    h1 = ET.SubElement(container, "h1")
    h1.text = path
    # Info
    if "info" in differences:
        reportFontInfo(differences["info"], container)
    # Features
    if "features" in differences:
        reportFontFeatures(differences["features"], container)
    # Groups
    if "groups" in differences:
        reportFontGroups(differences["groups"], container)
    # Kerning
    if "kerning" in differences:
        reportFontKerning(differences["kerning"], container)
    # Guidelines
    if "guidelines" in differences:
        reportFontGuidelines(differences["guidelines"], container)
    # Lib
    if "lib" in differences:
        reportFontLib(differences["lib"], container)
    # Layers
    if "layers" in differences:
        reportFontLayers(differences["layers"], container)

def reportFontInfo(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    h1 = ET.SubElement(container, "h1")
    h1.text = "Info"
    info1 = differences["info1"]
    info2 = differences["info2"]
    diffs = []
    for attr, data in sorted(differences.items()):
        if attr == "info1":
            continue
        if attr == "info2":
            continue
        value1 = "%s = %s" % (attr, _fancyRepr(data["value1"], attr))
        value2 = "%s = %s" % (attr, _fancyRepr(data["value2"], attr))
        diffs.append(("removed", value1))
        diffs.append(("added", value2))
    makeDiffTable(diffs, container)

def reportFontFeatures(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    h1 = ET.SubElement(container, "h1")
    h1.text = "Features"
    text1 = differences["text"]["value1"]
    text2 = differences["text"]["value2"]
    reportChangedText(text1, text2, container)

def reportFontGroups(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    if "removed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Removed Groups"
        diffs = [("removed", groupName) for groupName in sorted(differences["removed"])]
        makeDiffTable(diffs, container)
    if "added" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Added Groups"
        diffs = [("added", groupName) for groupName in sorted(differences["added"])]
        makeDiffTable(diffs, container)
    if "changed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Changed Groups"
        diffs = []
        for groupName, data in sorted(differences["changed"].items()):
            value1 = "%s = [%s]" % (groupName, ", ".join(data["value1"]))
            value2 = "%s = [%s]" % (groupName, ", ".join(data["value2"]))
            diffs.append(("removed", value1))
            diffs.append(("added", value2))
        makeDiffTable(diffs, container)

def reportFontKerning(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    if "removed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Removed Kerning"
        diffs = [("removed", _reprKerningPair(pair)) for pair in sorted(differences["removed"])]
        makeDiffTable(diffs, container)
    if "added" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Added Kerning"
        diffs = [("added", _reprKerningPair(pair)) for pair in sorted(differences["added"])]
        makeDiffTable(diffs, container)
    if "changed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Changed Kerning"
        diffs = []
        for pair, data in sorted(differences["changed"].items()):
            value1 = "%s = %s" % (_reprKerningPair(pair), _fancyRepr(data["value1"]))
            value2 = "%s = %s" % (_reprKerningPair(pair), _fancyRepr(data["value2"]))
            diffs.append(("removed", value1))
            diffs.append(("added", value2))
        makeDiffTable(diffs, container)

def _reprKerningPair(pair):
    return "(%s, %s)" % pair

def reportFontGuidelines(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    if "removed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Removed Guidelines"
        diffs = [("removed", _fancyRepr(guideline)) for guideline in differences["removed"]]
        makeDiffTable(diffs, container)
    if "added" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Added Guidelines"
        diffs = [("added", _fancyRepr(guideline)) for guideline in differences["added"]]
        makeDiffTable(diffs, container)
    if "changed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Changed Guidelines"
        for guideline in differences["changed"]:
            diffs = []
            for attr, data in guideline.items():
                if attr == "guideline1":
                    continue
                if attr == "guideline2":
                    continue
                if attr == ">naked name":
                    attr = "name"
                value1 = "%s = %s" % (attr, _fancyRepr(data["value1"]))
                value2 = "%s = %s" % (attr, _fancyRepr(data["value2"]))
                diffs.append(("removed", value1))
                diffs.append(("added", value2))
            makeDiffTable(diffs, container)

def _reprGuideline(guideline):
    attrs = []
    name = guideline.naked().name
    if name:
        attrs.append("name = %s" % _fancyRepr(name))
    angle = guideline.angle
    if angle is not None:
        attrs.append("angle = %s°" % _fancyRepr(angle))
    x = guideline.x
    if x is not None:
        attrs.append("x = %s" % _fancyRepr(x))
    y = guideline.y
    if y is not None:
        attrs.append("y = %s" % _fancyRepr(y))
    return ", ".join(attrs)

def reportFontLib(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    if "removed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Removed Lib Keys"
        diffs = [("removed", key) for key in sorted(differences["removed"])]
        makeDiffTable(diffs, container)
    if "added" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Added Lib Keys"
        diffs = [("removed", key) for key in sorted(differences["added"])]
        makeDiffTable(diffs, container)
    if "changed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Changed Lib Items"
        diffs = []
        for key, data in sorted(differences["changed"].items()):
            value1 = "%s = %s" % (key, pprint.pformat(data["value1"]))
            value2 = "%s = %s" % (key, pprint.pformat(data["value2"]))
            diffs.append(("removed", value1))
            diffs.append(("added", value2))
        makeDiffTable(diffs, container)

def reportFontLayers(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    if "removed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Removed Layers"
        diffs = [("removed", layerName) for layerName in sorted(differences["removed"])]
        makeDiffTable(diffs, container)
    if "added" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Added Layers"
        diffs = [("added", layerName) for layerName in sorted(differences["added"])]
        makeDiffTable(diffs, container)
    if "changed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Changed Layers"
        layerNames = [None]
        layerNames += sorted([layerName for layerName in differences["changed"].keys() if layerName is not None])
        for layerName in layerNames:
            data = differences["changed"][layerName]
            reportFontLayer(data, container)

def reportFontLayer(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    layer1 = differences["layer1"]
    layer2 = differences["layer2"]
    layerName = layer1.name
    if layer1 == layer1.font.defaultLayer:
        layerName = "(default)"
    h1 = ET.SubElement(container, "h1")
    h1.text = 'Layer: %s' % layerName
    diffs = []
    for attr, data in sorted(differences.items()):
        if attr == "layer1":
            continue
        if attr == "layer2":
            continue
        if attr == "glyphs":
            continue
        value1 = "%s = %s" % (attr, _fancyRepr(data["value1"], attr))
        value2 = "%s = %s" % (attr, _fancyRepr(data["value2"], attr))
        diffs.append(("removed", value1))
        diffs.append(("added", value2))
    if diffs:
        makeDiffTable(diffs, container)
    # Glyphs
    if "glyphs" in differences:
        reportFontGlyphs(differences["glyphs"], container)

def reportFontGlyphs(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    if "removed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Removed Glyphs"
        diffs = [("removed", glyphName) for glyphName in sorted(differences["removed"])]
        makeDiffTable(diffs, container)
    if "added" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Added Glyphs"
        diffs = [("added", glyphName) for glyphName in sorted(differences["added"])]
        makeDiffTable(diffs, container)
    if "changed" in differences:
        h1 = ET.SubElement(container, "h1")
        h1.text = "Changed Glyphs"
        for glyphName in sorted(differences["changed"].keys()):
            data = differences["changed"][glyphName]
            reportFontGlyph(data, container)

def reportFontGlyph(differences, parent):
    container = ET.SubElement(parent, "div", {"class" : "fileSection"})
    glyph1 = differences["glyph1"]
    glyph2 = differences["glyph2"]
    h1 = ET.SubElement(container, "h1")
    h1.text = 'Glyph: %s' % glyph1.name
    # non-visual data
    diffs = []
    needsVisualization = False
    for attr, data in sorted(differences.items()):
        if attr == "glyph1":
            continue
        if attr == "glyph2":
            continue
        if attr in ("contours", "components", "anchors"):
            needsVisualization = True
            continue
        if attr == "lib":
            reportFontLib(data, container)
        elif attr == "guidelines":
            reportFontGuidelines(data, container)
        else:
            value1 = "%s = %s" % (attr, _fancyRepr(data["value1"], attr))
            value2 = "%s = %s" % (attr, _fancyRepr(data["value2"], attr))
            diffs.append(("removed", value1))
            diffs.append(("added", value2))
    makeDiffTable(diffs, container)
    if needsVisualization:
        reportGlyphVisualization(differences, container)

def reportGlyphVisualization(differences, parent):
    glyph1 = differences["glyph1"]
    glyph2 = differences["glyph2"]
    data = [
        ("removed", drawGlyph(differences, "1")),
        ("added", drawGlyph(differences, "2")),
    ]
    makeDiffTable(data, parent)

def drawGlyph(differences, tag):
    glyph = differences["glyph" + tag]
    font = glyph.font
    upm = font.info.unitsPerEm
    if upm is None:
        upm = 1000
    pointSize = 300
    scale = pointSize / upm
    pixel = 1 / scale
    padding = pointSize * 0.2
    width = (glyph.width * scale) + (padding * 2)
    top = max((font.info.ascender, font.info.capHeight))
    bottom = min((0, font.info.descender))
    height = ((top - bottom) * scale) + (padding * 2)
    bot.newPage(width, height)
    bot.translate(padding, padding)
    bot.scale(scale)
    bot.translate(0, -font.info.descender)
    # Image
    # Metrics
    with bot.savedState():
        bot.fill(None)
        bot.stroke(0, 0, 0, 0.3)
        bot.strokeWidth(pixel)
        ys = set([
            font.info.descender,
            0,
            font.info.xHeight,
            font.info.ascender,
            font.info.capHeight,
        ])
        for y in ys:
            bot.line((0, y), (glyph.width, y))
        xs = set([
            0,
            glyph.width
        ])
        for x in xs:
            bot.line((x, bottom), (x, top))
    # Components
    pen = bot.BezierPath(glyphSet=glyph.layer)
    glyph.draw(pen, contours=False)
    bot.fill(0, 0, 0, 0.2)
    bot.drawPath(pen)
    # Contours
    pen = bot.BezierPath(glyphSet=glyph.layer)
    glyph.draw(pen, components=False)
    bot.fill(0, 0, 0, 0.8)
    bot.drawPath(pen)
    # Anchors
    if glyph.anchors:
        _drawAnchors(glyph.anchors, glyph, scale, pixel)
    # Component Differences
    if "components" in differences:
        componentDifferences = differences["components"]
        drawComponentDifferences(componentDifferences, glyph, tag, scale, pixel)
    # Contour Differences
    if "contours" in differences:
        contourDifferences = differences["contours"]
        drawContourDifferences(contourDifferences, glyph, tag, scale, pixel)
    # Anchor Differences:
    if "anchors" in differences:
        anchorDifferences = differences["anchors"]
        drawAnchorDifferences(anchorDifferences, glyph, tag, scale, pixel)
    # Convert to ET
    _, path = tempfile.mkstemp(suffix=".svg")
    bot.saveImage(path)
    f = open(path, "r")
    svg = f.read()
    f.close()
    os.remove(path)
    svg = _fromStringWithoutNamespace(svg)
    return svg

# Contours

def drawContourDifferences(differences, glyph, tag, scale, pixel):
    if tag == "1" and "removed" in differences:
        _drawContours(differences["removed"], glyph, scale, pixel, colorRemoved)
    if tag == "2" and "added" in differences:
        _drawContours(differences["added"], glyph, scale, pixel, colorAdded)
    if "changed" in differences:
        for contourDifferences in differences["changed"]:
            if "points" in contourDifferences:
                drawPointDifferences(contourDifferences["points"], glyph, tag, scale, pixel)

def drawPointDifferences(differences, glyph, tag, scale, pixel):
    if "removed" in differences and tag == "1":
        _drawPoints(differences["removed"], scale, pixel, colorRemoved)
    if "added" in differences and tag == "2":
        _drawPoints(differences["added"], scale, pixel, colorAdded)
    if "changed" in differences:
        points = [d["point" + tag] for d in differences["changed"]]
        _drawPoints(points, scale, pixel, colorChanged)

def _drawContours(components, glyph, scale, pixel, color):
    with bot.savedState():
        bot.fill(None)
        bot.stroke(*color)
        w = pixel * 2
        bot.strokeWidth(w)
        for component in components:
            pen = bot.BezierPath(glyphSet=glyph.layer)
            component.draw(pen)
            bot.drawPath(pen)

def _drawPoints(points, scale, pixel, color):
    with bot.savedState():
        for point in points:
            x = point.x
            y = point.y
            if point.type == "offcurve":
                s = pixel * 4
                shape = bot.oval
            elif point.type == "curve":
                s = pixel * 6.5
                shape = bot.oval
            else:
                s = pixel * 6
                shape = bot.rect
            h = s / 2
            r = (x - h, y - h, s, s)
            bot.fill(None)
            bot.stroke(1, 1, 1, 1)
            bot.strokeWidth(pixel * 2)
            shape(*r)
            bot.fill(*color)
            bot.stroke(None)
            shape(*r)

# Anchors

def drawAnchorDifferences(differences, glyph, tag, scale, pixel):
    if tag == "1" and "removed" in differences:
        _drawAnchors(differences["removed"], glyph, scale, pixel, colorRemoved)
    if tag == "2" and "added" in differences:
        _drawAnchors(differences["added"], glyph, scale, pixel, colorAdded)
    if "changed" in differences:
        anchors = set()
        for data in differences["changed"]:
            anchors.add(data["anchor" + tag])
        _drawAnchors(anchors, glyph, scale, pixel, colorChanged)

def _drawAnchors(anchors, glyph, scale, pixel, color=None):
    alwaysColor = color
    with bot.savedState():
        for anchor in anchors:
            if alwaysColor:
                color = alwaysColor
            else:
                color = anchor.color
                if color is None:
                    color = (0, 0, 0, 0.5)
            x = anchor.x
            y = anchor.y
            s = pixel * 6.5
            h = s / 2
            r = (x - h, y - h, s, s)
            bot.stroke(None)
            bot.fill(*color)
            bot.oval(*r)
            if alwaysColor is None:
                name = anchor.name
                if name:
                    pointSize = 10
                    bot.fontSize(pixel * pointSize)
                    bot.text(name, (x, y - s - h - pointSize), align="center")

# Components

def drawComponentDifferences(differences, glyph, tag, scale, pixel):
    if tag == "1" and "removed" in differences:
        _drawComponents(differences["removed"], glyph, scale, pixel, colorRemoved)
    if tag == "2" and "added" in differences:
        _drawComponents(differences["added"], glyph, scale, pixel, colorAdded)
    if "changed" in differences:
        components = set()
        for data in differences["changed"]:
            components.add(data["component" + tag])
        _drawComponents(components, glyph, scale, pixel, colorChanged)

def _drawComponents(components, glyph, scale, pixel, color):
    with bot.savedState():
        bot.fill(None)
        bot.stroke(*color)
        w = pixel * 2
        bot.strokeWidth(w)
        for component in components:
            pen = bot.BezierPath(glyphSet=glyph.layer)
            component.draw(pen)
            bot.drawPath(pen)

def _fromStringWithoutNamespace(xml):
    # https://stackoverflow.com/questions/13412496/python-elementtree-module-how-to-ignore-the-namespace-of-xml-files-to-locate-ma
    it = ET.iterparse(StringIO(xml))
    for _, el in it:
        prefix, has_namespace, postfix = el.tag.partition('}')
        if has_namespace:
            el.tag = postfix
    root = it.root
    return root

def makeDiffTable(data, parent):
    table = ET.SubElement(parent, "table", {"class" : "diffs"})
    for action, info in data:
        tokenClass = "diffAction" + action.title()
        tr = ET.SubElement(table, "tr")
        td = ET.SubElement(tr, "td", {"class" : tokenClass})
        if action == "removed":
            td.text = "-"
        else:
            td.text = "+"
        if isinstance(info, str):
            infoClass = "diffText" + action.title()
            td = ET.SubElement(tr, "td", {"class" : infoClass})
            pre = ET.SubElement(td, "pre")
            pre.text = info
        else:
            infoClass = "diffSVG" + action.title()
            td = ET.SubElement(tr, "td", {"class" : infoClass})
            td.append(info)

def _fancyRepr(value, attr=None):
    if attr == "unicodes":
        value = [hex(value).upper()[2:].zfill(4) for value in value]
        value = "[%s]" % ", ".join(value)
        return value
    return repr(value)



colorRemoved = (0.95, 0, 0)
colorAdded = (0, 0.9, 0)
colorChanged = (0.9, 0.5, 0)
rgbColorStrings = dict(
    colorRemoved=", ".join([str(int(255 * i)) for i in colorRemoved]),
    colorAdded=", ".join([str(int(255 * i)) for i in colorAdded]),
    colorChanged=", ".join([str(int(255 * i)) for i in colorChanged])
)
css = """
:root {
    --base-font-weight: 300;
    --bold-font-weight: 600;

    --file-border: 1px solid rgba(0, 0, 0, 0.4);
    --file-background-color: rgba(0, 0, 0, 0.01);

    --removed-color: rgb(__colorRemoved__);
    --removed-background-color: rgba(__colorRemoved__, 0.05);
    --removed-block-color: rgba(__colorRemoved__, 0.5);
    --added-color: rgb(__colorAdded__);
    --added-background-color: rgba(__colorAdded__, 0.05);
    --added-block-color: rgba(__colorAdded__, 0.5);
    --changed-color: rgb(__colorChanged__);
    --changed-background-color: rgba(__colorChanged__, 0.01);
}

body {
    margin: 5em;
    font-family: -apple-system;
    font-size: 15 px;
    font-weight: var(--base-font-weight);
}

/* Tame Everything */

h1, h2, h3, h4, h5, h6 {
    margin: 0;
    padding: 0;
    font-size: 1em;
    font-style: normal;
    font-weight: var(--base-font-weight);
}

ul {
    margin: 0;
    padding: 0;
    list-style: none;
}

li {
    margin: 0;
    padding: 0;
}

p {
    margin: 0;
    padding: 0;
}

table {
    width: 100%;
    margin: 0;
    padding: 0;
    border-collapse: collapse;
    border-spacing: 0;
    empty-cells: show;
    vertical-align: text-top;
}

pre {
    margin: 0;
    padding: 0;
    font-family: SFMono-Regular, Consolas, Menlo, monospace;
}

/* Globals */

h1 {
    margin-top: 0.5em;
    font-weight: var(--bold-font-weight);
}

/* Root */

.root {}

.root h1 {
    margin-top: 1.5em;
    padding-bottom: 0.5em;
    margin-bottom: 0.5em;
    border-bottom: 1px solid black;
    font-size: 1.25em;
}

.added {
    margin-top: var(--section-margin-top);
}

.removed {
    margin-top: var(--section-margin-top);
}

.changed {
    margin-top: var(--section-margin-top);
}

/* Changed File */

.file {
    margin-top: 1em;
    margin-bottom: 1em;
    padding: 1em;
    border: var(--file-border);
    background-color: var(--file-background-color);
}

.file h1 {
    margin-top: 0;
    margin-bottom: 1em;
    padding-bottom: 0.5em;
    border-bottom: 1px solid rgba(0, 0, 0, 0.2);
    font-size: 1em;
    font-weight: normal;
}

.file h2.binaryFileWarning {
    margin-top: 0.5em;
    font-size: 1em;
    font-style: italic;
}

/* Changed File Section */

.fileSection {
    border-left: var(--file-border);
    background-color: var(--file-background-color);
    padding: 1em;
    padding-right: 0;
}

.fileSection h1 {
    margin-bottom: 0.5em;
    padding: 0;
    border-bottom: none;
    font-weight: var(--bold-font-weight);
    font-size: 1em;
}

/* Diffs */

table.diffs {
    font-family: SFMono-Regular, Consolas, Menlo, monospace;
    font-size: 0.8em;
    margin-bottom: 1.5em;
}
td.diffActionAdded {
    width: 1em;
    padding-top: 0.25em;
    padding-bottom: 0.25em;
    background-color: var(--added-block-color);
    text-align: center;
}
td.diffTextAdded {
    padding-top: 0.25em;
    padding-bottom: 0.25em;
    padding-left: 0.5em;
    background-color: var(--added-background-color);
}
td.diffSVGAdded {
    background-color: var(--added-background-color);
}
td.diffActionRemoved {
    width: 1em;
    padding-top: 0.25em;
    padding-bottom: 0.25em;
    background-color: var(--removed-block-color);
    text-align: center;
    color: white;
}
td.diffTextRemoved {
    padding-top: 0.25em;
    padding-bottom: 0.25em;
    padding-left: 0.5em;
    padding-right: 1em;
    background-color: var(--removed-background-color);
}
td.diffSVGRemoved {
    background-color: var(--removed-background-color);
}
"""
for key, value in rgbColorStrings.items():
    css = css.replace("__%s__" % key, value)

def makeHTMLElement():
    container = ET.Element("html")
    head = ET.SubElement(container, "head")
    style = ET.SubElement(head, "style")
    style.text = css
    body = ET.SubElement(container, "body")
    return container

def makeHTMLString(element):
    indent(element)
    text = ET.tostring(
        element,
        encoding="utf8",
        method="html"
    )
    text = text.decode("utf8")
    return text


# I am so tired of ET not supporting pretty printing.
# ---------------------------------------------------

def indent(elem, whitespace="    ", level=0):
    # http://effbot.org/zone/element-lib.htm#prettyprint
    i = "\n" + level * whitespace
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + whitespace
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, whitespace, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


# ----
# Test
# ----

if __name__ == "__main__":
    directory = os.path.dirname(__file__)
    directory = os.path.dirname(directory)
    directory = os.path.dirname(directory)
    directory = os.path.dirname(directory)
    directory = os.path.join(directory, "test", "diff")
    directory1 = os.path.join(directory, "0000-00-00-00-00")
    directory2 = os.path.join(directory, "0000-00-00-00-01")

    differences = diffDirectories(
        directory1,
        directory2,
        onlyCompareFontDefaultLayers=False
    )
    report = makeRootReport(differences)
    path = os.path.join(os.path.dirname(__file__), "test.html")
    f = open(path, "w")
    f.write(report)
    f.close()