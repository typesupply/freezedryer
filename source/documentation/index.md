# Freeze Dryer

A very minimal, file-based font versioning and backup tool.

## WTF!? How do I?

Before we get to that, some terminology:

- project: All of the files for a font development project that can be stored within one directory and any number of sub-directories.
- root: The top most directory in the project.
- state: A version of the project at an instant in time.
- archive: The location where the states are stored.
- commit: Put the current state of the project in the archive.

Freeze Dryer doesn't require a standard project structure (see the reference section below for complete details on this), but here is one of my project structures (with <- annotations) as an example of these terms:

```

/Inverso <- this is a project and this is the root of the project
  Master-Primo.ufo
  Master-Primo Italico.ufo
  Master-Ultimo.ufo
  Master-Ultimo Italico.ufo
  freeze dryer.plist
  /features
    italic.fea
    italic-c.fea
    roman.fea
    roman-c.fea
  /interpolation
	italic.designspace
    roman.designspace
  /proofs
  	masters.indd
  	instances.indd
  /scripts
    italic starter.py
  /ignore
  	secret stuff.txt
  	more secrets.md
  /archive <- this is the archive
  	/2020-03-15-04-02 <- this is a state
  		2020-03-15-04-02 glyphs.pdf
  		sketch.ufo
  	/2020-03-22-19-01 <- this is another state
  		2020-03-22-19-01 glyphs.pdf
  		light sketch.ufo
  		bold sketch.ufo
  		/proofs
  		  sketch.indd
```

Okay, so, here's how to use it:

1. **Initialize a project.** Select the "Initialize Project..." menu item and select the root directory of your project. This can be an existing project you are working on with files and stuff already in it. This will create a file named `freeze dryer.plist` in the project's root. The project's settings window will open.
2. **Set your settings if you don't like the defaults.** The default location for the archive is a directory in the root named `archive` but you can pick any directory you way. It can even be a completely separate location, such as a sub-directory in your Dropbox directory. You can have the UFOs compressed to UFOZs if you want to not make Dropbox have a freak out.
3. **If you already have some files in your project, make an initial commit.** See that "Commit" tab? Click it, type "Initial Commit" into the text box and press the "Commit State" button.
4. **Do some type designing.** When you are ready to commit to the archive, move to the next step. When should you commit? That's up to you.
5. **Commit your changes.** Select the "Commit Project..." menu item. Select your project's root directory. The commit window will open. Type a message describing why you are putting this in the archive. Or don't type anything. It's optional. Press the "Commit State" button.

Repeat steps 4-5 until you are completely finished with the project. If you want to see a state, go into the archive directory in the Finder and look at it. It's just a regular directory containing regular files.

If you need to change your project settings, you can do so at any time by sellecting the "Project Settings..." menu item and selecting your project's root directory.

That's all it does. The end.

## Reference

### Ignoring Files

If you want files to be ignored, you can specify them in the settings window. The pattern matching syntax is the same as Python's [glob module](https://docs.python.org/3.5/library/glob.html) syntax. If a pattern starts with `/`  the pattern is relative to the root of the project. Otherwise the pattern may also match at any level within the project.

### File Structure

There is no specific structure. There are, however, some reserved file names and locations:

#### /ignore

Anything inside of a root level directory named `ignore` will not be included in a state.

#### /archive

The default location for the archive is in a root level directory named `archive.` Therefore, anything in a directory with this name will not be included in a state.

#### /freeze dryer.plist

The settings for this tool are stored in a root level file named `freeze dryer.plist`.

#### State Storage

States will be stored in a time stamped directory. The time stamp is in Coordinated Universal Time in this format: `####-##-##-##-##` where the components are: `year-month-day-hour-minute`. It's only granular to the minute, but I don't need more granularity in the context of my font development projects.

The following files will be written as needed:

- (time stamp) message.txt (optional): This will contain a message given by the user during commit.
- (time stamp) glyphs.txt (optional): This will contain a proof of all glyphs in all UFOs in the state.