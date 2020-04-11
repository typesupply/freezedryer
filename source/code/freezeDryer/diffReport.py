import os
from io import StringIO
import tempfile
import difflib
import html
import pprint
import drawBot as bot

# ------
# Output
# ------

from xml.etree import cElementTree as ET

# HTML
# ----

def makeDiffReport(differences):
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
    bot.newDrawing()
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
    # XXX hack around a bug in defcon
    from fontParts.fontshell import RGuideline
    if isinstance(value, RGuideline):
        if value.naked().name == "":
            value.naked().name = None
            r = repr(value)
            value.naked().name = ""
            return r
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
    --file-background-color: rgba(0, 0, 0, 0.02);

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
    margin: 3em;
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
    import diff

    directory = os.path.dirname(__file__)
    directory = os.path.dirname(directory)
    directory = os.path.dirname(directory)
    directory = os.path.dirname(directory)
    directory = os.path.join(directory, "test", "diff")
    directory1 = os.path.join(directory, "0000-00-00-00-00")
    directory2 = os.path.join(directory, "0000-00-00-00-01")

    differences = diff.diffDirectories(
        directory1,
        directory2,
        onlyCompareFontDefaultLayers=False
    )
    report = makeDiffReport(differences)
    path = os.path.join(os.path.dirname(__file__), "test.html")
    f = open(path, "w")
    f.write(report)
    f.close()