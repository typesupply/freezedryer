import os
from defconAppKit.controls.fontList import fontWidthWeightSort
import drawBot as bot
from fontParts.world import OpenFont

# ----
# Main
# ----

def makeGlyphSetProof(stateDirectory, stamp):
    from freezeDryer.core import gatherUFOPaths
    paths = gatherUFOPaths(stateDirectory)
    fonts = [OpenFont(path, showInterface=False) for path in paths]
    fonts = fontWidthWeightSort(fonts)
    makeAllFontsDefaultLayerPages(stateDirectory, stamp, fonts)
    for font in fonts:
        makeOneFontAllLayersPages(stateDirectory, stamp, font)
        for layer in font.layerOrder:
            makeOneFontOneLayerPages(stateDirectory, stamp, font, layer)
    path = os.path.join(stateDirectory, stamp + " glyphs.pdf")
    bot.saveImage(path)

# ---------------
# Specific Proofs
# ---------------

# All Fonts: Default Layer

def makeAllFontsDefaultLayerPages(stateDirectory, stamp, fonts):
    order = []
    for font in fonts:
        for name in font.glyphOrder:
            if name not in order:
                order.append(name)
    glyphs = []
    for name in order:
        for font in fonts:
            if name in font:
                glyphs.append(font[name])
    makePages(
        glyphs,
        pointSize=75,
        lineHeight=75,
        tracking=100,
        layers=None,
        title="%s | All Fonts" % stamp,
        drawFill=True,
        drawMarkColor=True,
        drawMetrics=False,
        drawName=False
    )

# One Font: All Layers

def makeOneFontAllLayersPages(stateDirectory, stamp, font):
    glyphs = []
    for name in font.glyphOrder:
        for layer in font.layers:
            if name in layer:
                glyphs.append(layer[name])
                break
    makePages(
        glyphs,
        pointSize=75,
        lineHeight=75,
        tracking=100,
        layers=font.layerOrder,
        title="%s | %s : All Layers" % (stamp, os.path.relpath(font.path, stateDirectory)),
        drawFill=True,
        drawMarkColor=True,
        drawMetrics=False,
        drawName=False
    )

def makeOneFontOneLayerPages(stateDirectory, stamp, font, layerName):
    layer = font.getLayer(layerName)
    glyphs = []
    for name in font.glyphOrder:
        if name in layer:
            glyphs.append(layer[name])
    makePages(
        glyphs,
        pointSize=75,
        lineHeight=75,
        tracking=100,
        layers=None,
        title="%s | %s : %s" % (stamp, os.path.relpath(font.path, stateDirectory), layerName),
        drawFill=True,
        drawMarkColor=True,
        drawMetrics=True,
        drawName=True
    )

# -----
# Tools
# -----

def makePages(glyphs, pointSize=150, lineHeight=150, tracking=0, layers=None, title="", **drawingKwargs):
    pageWidth = 1280
    pageHeight = 1024
    margin = 50
    topMargin = 100
    box = (margin, margin, pageWidth - (margin * 2), pageHeight - margin - topMargin)
    glyphs = list(glyphs)
    while glyphs:
        bot.newPage(pageWidth, pageHeight)
        with bot.savedState():
            bot.strokeWidth(0.5)
            bot.stroke(0, 0, 0, 1)
            bot.font("SanFranciscoText-Light", 15)
            bot.line((margin, pageHeight - topMargin + 10), (pageWidth - margin, pageHeight - topMargin + 10))
            bot.text(title, (margin, pageHeight - topMargin + 20))
        glyphs = drawGlyphsInBox(
            glyphs,
            box,
            pointSize=100,
            lineHeight=150,
            tracking=100,
            layers=layers,
            **drawingKwargs
        )

def drawGlyphsInBox(glyphs, box, pointSize=150, lineHeight=150, tracking=0, layers=None, **drawingKwargs):
    if not glyphs:
        return
    x, y, boxWidth, boxHeight = box
    scale = pointSize / glyphs[0].font.info.unitsPerEm
    with bot.savedState():
        # move to top left
        bot.translate(x, y + boxHeight)
        # draw lines
        drawnGlyphs = []
        maxLineWidth = boxWidth
        maxLineCount = boxHeight // lineHeight
        for lineIndex in range(maxLineCount):
            bot.translate(0, -lineHeight)
            line = []
            lineWidth = 0
            for glyph in glyphs:
                glyph = glyphs[0]
                glyphs = glyphs[1:]
                if not line:
                    line.append(glyph)
                    lineWidth += glyph.width
                    drawnGlyphs.append(glyph)
                elif (lineWidth + tracking + glyph.width) * scale > maxLineWidth:
                    glyphs.insert(0, glyph)
                    break
                else:
                    line.append(glyph)
                    lineWidth += tracking + glyph.width
                    drawnGlyphs.append(glyph)
            # draw the line
            drawGlyphs(line, pointSize, tracking=tracking, layers=layers, **drawingKwargs)
            # stop if out of glyphs
            if not glyphs:
                break
    # return the overflow
    return glyphs

def drawGlyphs(glyphs, pointSize, tracking=0, layers=None, **drawingKwargs):
    if not glyphs:
        return
    with bot.savedState():
        scale = pointSize / glyphs[0].font.info.unitsPerEm
        oneUnit = 1 / scale
        bot.scale(scale)
        for glyph in glyphs:
            drawGlyph(glyph, scale=oneUnit, layers=layers, **drawingKwargs)
            bot.translate(glyph.width + tracking, 0)

def drawGlyph(glyph, scale=1.0, layers=None, drawFill=True, drawMarkColor=True, drawMetrics=True, drawName=True):
    font = glyph.font
    # metrics
    verticalMetrics = [0, font.info.descender, font.info.xHeight, font.info.capHeight, font.info.ascender]
    bottom = min(verticalMetrics)
    top = max(verticalMetrics)
    height = abs(bottom) + top
    width = glyph.width
    if drawMetrics:
        with bot.savedState():
            bot.strokeWidth(0.1 + scale)
            bot.stroke(0, 0, 0, 0.25)
            for y in set(verticalMetrics):
                bot.line((0, y), (width, y))
            bot.line((0, bottom), (0, top))
            bot.line((width, bottom), (width, top))
    # mark color
    if drawMarkColor:
        if glyph.markColor:
            with bot.savedState():
                r, g, b, a = glyph.markColor
                bot.fill(r, g, b, a)
                bot.rect(0, bottom, glyph.width, height)
    # name
    if drawName:
        with bot.savedState():
            s = 8 * scale
            bot.font("SanFranciscoText-Light", s)
            bot.fill(0, 0, 0, 0.5)
            bot.text(glyph.name, (0, bottom - (s * 1.5)))
    # fill
    if drawFill:
        if layers is None:
            bot.drawGlyph(glyph)
        else:
            glyphName = glyph.name
            with bot.savedState():
                for layerName in reversed(font.layerOrder):
                    layer = font.getLayer(layerName)
                    if glyphName in layer:
                        color = layer.color
                        if color is None:
                            color = (0, 0, 0, 0.5)
                        r, g, b, a = color
                        bot.fill(r, g, b, a)
                        bot.drawGlyph(layer[glyphName])
