import os
import shutil
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
        archiveDirectory=getDefaultArchiveDirectory(root)
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
    path = getSettingsPath(root)
    plistlib.writePlist(settings, path)

def getArchiveDirectory(root, settings):
    archiveDirectory = settings.get(root)
    if archiveDirectory is None:
        archiveDirectory = getDefaultArchiveDirectory(root)
    return archiveDirectory

def getDefaultArchiveDirectory(root):
    return os.path.join(root, "archive")

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
    # make the state directory
    stateDirectory = getStatePath(archiveDirectory, stamp)
    os.mkdir(stateDirectory)
    # copy files and directories
    files, directories = gatherProjectContentPaths(root)
    for sourcePath in files:
        statePath = os.path.join(stateDirectory, os.path.basename(sourcePath))
        shutil.copy2(sourcePath, statePath)
    for sourcePath in directories:
        statePath = os.path.join(stateDirectory, os.path.basename(sourcePath))
        shutil.copytree(sourcePath, statePath)
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

alwaysIgnore = """
ignore
archive
""".strip().splitlines()

def gatherProjectContentPaths(root):
    files = []
    directories = []
    for fileName in os.listdir(root):
        if fileName.startswith("."):
            continue
        if fileName in alwaysIgnore:
            continue
        path = os.path.join(root, fileName)
        if os.path.splitext(fileName)[-1].lower() == ".ufo":
            directories.append(path)
        elif os.path.isdir(path):
            directories.append(path)
        else:
            files.append(path)
    return files, directories

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
