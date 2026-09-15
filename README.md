# game-backup-tool
A game backup tool that saves your savegames every X minutes

# IMPORTANT
You need an existing WinRAR installation to use my program!

# About me
I'm not a programmer. I created this program with CLAUDE via vibecoding. So actually I have no idea what I'm doing. LOL The program works fine. I tested it with multiple games and it did what it should do. :)

# What is it?
This tool automatically creates timestamped backups of your game's save files at a configurable interval.  
When setting up the tool, you choose the location of your game's save files, the destination folder for the backups, and the location of your existing WinRAR installation. You can then configure how often a backup should be created and how many backup archives should be kept.  
Each backup is stored as a separate WinRAR archive with the current date and time in its filename. Existing backup archives are never overwritten.  
The tool also checks whether the savegame has actually changed since the last backup. If nothing has changed, no new archive is created. This prevents your backup folder from being filled with identical copies of the same savegame.  
You can also define how many backup archives should be kept. For example, you can keep the last ten, twenty, fifty, or one hundred backups. Once the configured limit is reached, the oldest backup is automatically removed when a new backup is created.  
This allows you to keep a rolling history of your savegames without having to manage the backup files manually.  
The tool can be left running while playing, or started manually whenever you want to create a backup.  
WinRAR must already be installed on your system. WinRAR is not included with this software and is not distributed with it.  
