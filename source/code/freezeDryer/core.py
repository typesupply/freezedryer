import os
import shutil
import glob
import time
import plistlib
import re

# --------
# Settings
# --------

def getDefaultSettings(root):
    settings = dict(
        formatVersion=0,
        compressUFOs=False,
        makeGlyphSetProof=False,
        makeVisualDiffsReport=False,
        normalizeDataInVisualDiffsReport=True,
        onlyDefaultLayerInVisualDiffsReport=True,
        archiveDirectory=getDefaultArchiveDirectory(root),
        ignore=getDefaultIgnorePatterns()
    )
    return settings

def getSettingsPath(root):
    return os.path.join(root, "freeze dryer.plist")

def haveSettings(root):
    path = getSettingsPath(root)
    return os.path.exists(path)

def readSettings(root):
    path = getSettingsPath(root)
    settings = getDefaultSettings(root)
    settings.update(plistlib.readPlist(path))
    return settings

def writeSettings(root, settings):
    settings = dict(settings)
    if settings["archiveDirectory"] == getDefaultArchiveDirectory(root):
        del settings["archiveDirectory"]
    if settings["ignore"] == getDefaultIgnorePatterns():
        del settings["ignore"]
    path = getSettingsPath(root)
    plistlib.writePlist(settings, path)

def getArchiveDirectory(root, settings):
    archiveDirectory = settings.get("archiveDirectory")
    if archiveDirectory is None:
        archiveDirectory = getDefaultArchiveDirectory(root)
    return archiveDirectory

def getDefaultArchiveDirectory(root):
    return os.path.join(root, "archive")

def getDefaultIgnorePatterns():
    patterns = """
    /archive
    /ignore
    *.idlk
    """
    patterns = [line.strip() for line in patterns.splitlines() if line.strip()]
    return patterns


# ----------
# Initialize
# ----------

def isViableRoot(directory):
    """
    Determine if the given directory is a
    viable candidate to be a root.

    XXX:
    walk an arbitrary number of levels up
    to make sure this isn't already in a project?
    """
    # is there a settings path?
    if haveSettings(directory):
        return False, "The selected directory is already in use by a project."
    return True, ""

def initializeProject(root, settings):
    """
    Initialize a project at the given root.
    """
    writeSettings(root, settings)
    archiveDirectory = getArchiveDirectory(root, settings)
    if archiveDirectory == getDefaultArchiveDirectory(root):
        if not os.path.exists(archiveDirectory):
            os.mkdir(archiveDirectory)


# -----
# Diffs
# -----

statePattern = re.compile("\d\d\d\d-\d\d-\d\d-\d\d-\d\d$")

def getDiffStateCandidates(root):
    states = []
    settings = readSettings(root)
    directory = getArchiveDirectory(root, settings)
    for fileName in reversed(sorted(os.listdir(directory))):
        if not statePattern.match(fileName):
            continue
        states.append(fileName)
    states.insert(0, "Current")
    return states

def compileDiffReport(root, state1, state2, normalize=False, onlyCompareFontDefaultLayers=True):
    from freezeDryer import diff
    from freezeDryer import diffReport
    rootSettings = readSettings(root)
    archiveDirectory = getArchiveDirectory(root, rootSettings)
    # normalize the paths for safety
    root = os.path.normpath(root)
    archiveDirectory = os.path.normpath(archiveDirectory)
    # locate the states
    if state1 == "Current":
        state1 = root
    else:
        state1 = os.path.join(archiveDirectory, state1)
    if state2 == "Current":
        state2 = root
    else:
        state2 = os.path.join(archiveDirectory, state2)
    # locate files that should be ignored
    state1IgnoredPaths = []
    if haveSettings(state1):
        state1Settings = readSettings(state1)
        state1IgnoredPaths = gatherIgnoredPaths(state1, state1Settings["ignore"])
    state2IgnoredPaths = []
    if haveSettings(state2):
        state2Settings = readSettings(state2)
        state2IgnoredPaths = gatherIgnoredPaths(state2, state2Settings["ignore"])
    # compile
    differences = diff.diffDirectories(
        state1,
        state2,
        ignorePaths1=state1IgnoredPaths,
        ignorePaths2=state2IgnoredPaths,
        onlyCompareFontDefaultLayers=onlyCompareFontDefaultLayers,
        normalizeFontContours=normalize,
        normalizeFontComponents=normalize,
        normalizeFontAnchors=normalize,
        normalizeFontGuidelines=normalize
    )
    report = diffReport.makeDiffReport(differences)
    return report

# ------
# Commit
# ------

def makeTimeStamp():
    return time.strftime("%Y-%m-%d-%H-%M", time.gmtime())

def getStatePath(archiveDirectory, stamp):
    return os.path.join(archiveDirectory, stamp)

def canPerformCommit(root):
    """
    Determine if a commit can be performed.
    """
    # missing settings
    if not haveSettings(root):
        return False, "Settings are missing."
    settings = readSettings(root)
    # missing archive directory
    archiveDirectory = getArchiveDirectory(root, settings)
    if not os.path.exists(archiveDirectory):
        return False, "Archive is missing."
    # stamp already exists
    stamp = makeTimeStamp()
    stateDirectory = getStatePath(archiveDirectory, stamp)
    if os.path.exists(stateDirectory):
        return False, "A state directory with this same time stamp already exists."
    return True, stamp

def performCommit(root, stamp, message=None, progressBar=None):
    settings = readSettings(root)
    if progressBar is not None:
        tickCount = 4
        tickCount += settings["compressUFOs"]
        tickCount += settings["makeVisualDiffsReport"]
        tickCount += settings["makeGlyphSetProof"]
        progressBar.setTickCount(tickCount)
    if progressBar:
        progressBar.update("Setting up state...")
    archiveDirectory = getArchiveDirectory(root, settings)
    # normalize the paths for safety
    root = os.path.normpath(root)
    archiveDirectory = os.path.normpath(archiveDirectory)
    # make the state directory
    stateDirectory = getStatePath(archiveDirectory, stamp)
    # locate files that should be ignored
    ignorePatterns = settings["ignore"]
    ignoredPaths = gatherIgnoredPaths(root, ignorePatterns)
    def ignoreArchiveFunction(path, names):
        ignore = []
        for name in names:
            if path in ignoredPaths:
                return names
            p = os.path.join(path, name)
            if p == archiveDirectory:
                return [name]
            if p in ignoredPaths:
                ignore.append(name)
        return ignore
    # copy the whole root to the state directory
    if progressBar:
        progressBar.update("Copying files...")
    shutil.copytree(root, stateDirectory, ignore=ignoreArchiveFunction)
    # remove ignored directories
    for path in ignoredPaths:
        base = os.path.relpath(path, root)
        path = os.path.join(stateDirectory, base)
        if not os.path.exists(path):
            continue
        if os.path.isdir(path):
            # there shouldn't be anything there,
            # but fail if there is just to be safe
            assert not list(os.listdir(path))
            shutil.rmtree(path)
    # write the message
    if message:
        message = message.encode("utf8")
        messagePath = os.path.join(stateDirectory, makeMessageFileName(stamp))
        f = open(messagePath, "wb")
        f.write(message)
        f.close()
    # compress UFOs
    if settings["compressUFOs"]:
        if progressBar:
            progressBar.update("Compressing UFOs...")
        recursivelyCompressUFOs(stateDirectory)
    # make the diffs
    if settings["makeVisualDiffsReport"]:
        if progressBar:
            progressBar.update("Making visual differences report...")
        candidates = getDiffStateCandidates(root)
        candidates.remove("Current")
        candidates.remove(stamp)
        candidates.sort()
        if candidates:
            report = compileDiffReport(
                root,
                candidates[-1],
                stamp,
                normalize=settings["normalizeDataInVisualDiffsReport"],
                onlyCompareFontDefaultLayers=settings["onlyDefaultLayerInVisualDiffsReport"]
            )
            report = report.encode("utf8")
            reportPath = os.path.join(stateDirectory, makeDiffReportFileName(stamp))
            f = open(reportPath, "wb")
            f.write(report)
            f.close()
    # make the proofs
    if settings["makeGlyphSetProof"]:
        if progressBar:
            progressBar.update("Making glyph set proof...")
        from freezeDryer import proof
        proof.makeGlyphSetProof(stateDirectory, stamp, makeProofFileName(stamp))

def makeMessageFileName(stamp):
    return stamp + " message.txt"

def makeProofFileName(stamp):
    return stamp + " glyphs.pdf"

def makeDiffReportFileName(stamp):
    return stamp + " diffs.html"

# -----
# Tools
# -----

def findRoot(directory, level=0):
    """
    Find the root directory for a project
    for any given directory <= 10 sub-directories
    below the root directory.
    """
    if haveSettings(directory):
        return directory
    level += 1
    if level <= 10:
        return findRoot(os.path.dirname(directory), level)
    return None

def gatherIgnoredPaths(directory, ignorePatterns, level=0):
    found = []
    # match file names
    for pattern in ignorePatterns:
        if pattern.startswith("/") and level > 0:
            continue
        elif pattern.startswith("/"):
            pattern = pattern[1:]
        fullPattern = os.path.join(directory, pattern)
        found += glob.glob(fullPattern)
    # recurse through sub-directories
    level += 1
    for fileName in os.listdir(directory):
        if os.path.splitext(fileName)[-1].lower() == ".ufo":
            continue
        fullPath = os.path.join(directory, fileName)
        if fullPath in found:
            continue
        if os.path.isdir(fullPath):
            found += gatherIgnoredPaths(fullPath, ignorePatterns, level)
    return found

# ---------------
# UFO Compression
# ---------------

def gatherUFOPaths(directory):
    ufos = []
    for fileName in os.listdir(directory):
        path = os.path.join(directory, fileName)
        if os.path.splitext(fileName)[-1].lower() in (".ufo", ".ufoz"):
            ufos.append(path)
        elif os.path.isdir(path):
            ufos += gatherUFOPaths(path)
    return ufos

def recursivelyCompressUFOs(directory):
    paths = gatherUFOPaths(directory)
    for path in paths:
        if os.path.splitext(path)[-1].lower() == ".ufoz":
            continue
        convertUFOToUFOZ(path)

def convertUFOToUFOZ(path):
    ufozPath = os.path.splitext(path)[0] + ".ufoz"
    zipPath = shutil.make_archive(
        ufozPath,
        "zip",
        os.path.dirname(path),
        os.path.basename(path)
    )
    os.rename(zipPath, ufozPath)
    shutil.rmtree(path)
