import os
import itertools
import filecmp
from fontTools.ufoLib import fontInfoAttributesVersion3

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
        different = filecmp.cmp(path1, path2)
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
    guidelines = diffGuidelines(font1, font2)
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
        pointDifferences["added"] = removed
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
