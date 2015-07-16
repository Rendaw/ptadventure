`polytaxis-adventure` is a browser for files indexed by `polytaxis-monitor`.

# Installation

## Linux

1. Install Python 3, pip, Qt, and `pyqt5` using your distribution's package manager.
2. Run
```
pip install https://github.com/Rendaw/ptadventure.git
```

## Mac OSX

1. Install homebrew
2. Run
```
brew install --HEAD rendaw/tap/polytaxis-adventure
```

# Configuration

`polytaxis-adventure` requires no configuration to browse the index, but configuration may be necessary to use advanced features.

## Launching Applications

To launch applications from `polytaxis-adventure`, you must create a launcher configuration file.

1. Run and close `polytaxis-adventure` from a terminal
2. The output will contain a line with the expected `launchers.json` file path.
3. Create and edit `launchers.json` at the expected path.

`launchers.json` has the following format:

```json
[
	{
		"name": "launcher name",
		"keys": ["file extension", "*", ...],
		"command": ["executable or script", "argument" or "{all-files}" or {"file"}],
		"unwrap": true,
	},
	...
]
```

`name` is the name of the command displayed in the open button/menu.

`keys` is a list of file extensions or `*`.  The open button/menu shows the launchers that matched the most files in the selection/display.  If `*` is included, the launcher will be displayed for all files.

`command` is the command to run, plus a template of its arguments.  The special argument "{all-files}" in "command" is expanded to all selected files or all displayed files if none are selected.  The special argument "{one-file}" in "command" is expanded to one files, and the command is run for each selected file (displayed file, if none are selected) individually.

`unwrap` indicates whether the paths should be translated to use `polytaxis-unwrap`.  This argument is optional and defaults to `true`.

An example `launchers.json`:
```json
[
	{
		"name": "mpv music",
		"keys": [
			".mp3", ".mp3.p",
			".aac", ".aac.p", 
			".ogg", ".ogg.p", 
			".wma", ".wma.p", 
			".mp4", ".mp4.p",
			".m4a", ".m4a.p"
		],
		"command": ["xfce4-terminal", "-x", "mpv", "--no-audio-display", "{all-files}"]
	},
	{
		"name": "collect",
		"keys": ["*"],
		"command": ["cp", "{one-file}", "/home/rendaw/pt-collection"],
		"unwrap": false
	}
]
```

`mpv music` will open all files with `mpv` in a new terminal.

`export` will copy files to `/home/rendaw/pt-collection`.

# Support

Ask questions and raise issues on the GitHub issue tracker.

See Contributing below for information about prioritizing issues.

# Contributing

1. Develop and submit pull requests.

2. Fund development via https://www.bountysource.com/
