import os
import shutil
import glob
import time
import plistlib

# --------
# Settings
# --------

def getDefaultSettings(root):
    settings = dict(
        formatVersion=0,
        compressUFOs=False,
        makeGlyphSetProof=True,
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

def performCommit(root, stamp, message=None):
    settings = readSettings(root)
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
        messagePath = os.path.join(stateDirectory, stamp + " message.txt")
        f = open(messagePath, "wb")
        f.write(message)
        f.close()
    # compress UFOs
    if settings["compressUFOs"]:
        recursivelyCompressUFOs(stateDirectory)
    # make the proofs
    if settings["makeGlyphSetProof"]:
        from freezeDryer import proof
        proof.makeGlyphSetProof(stateDirectory, stamp)

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
