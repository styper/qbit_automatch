# qbit_automatch

### Description:
Script to match torrent files with renamed files, then updating qBittorrent accordingly.  
The script uses length in bytes and extension to match the files, torrent files don't have individual file hashes so this is what I could do.  
All the torrent files must have a match in the search dir, otherwise the script will fail.

### Dependencies:

[bencode.py](https://github.com/fuzeman/bencode.py)  
[psutil](https://github.com/giampaolo/psutil)  
[rapidfuzz](https://github.com/maxbachmann/RapidFuzz)

```
python -m pip install bencode.py psutil rapidfuzz
```
or
```
python3 -m pip install bencode.py psutil rapidfuzz
```
or
```
pip install bencode.py psutil rapidfuzz
```

### Usage:
```
usage: qbit_automatch.py [-h] -a HASH -s PATH [-b PATH] [-f N] [-d]

required arguments:
  -a HASH, --hash HASH  Torrent hash. In qBittorrent right click the torrent -> copy -> hash
  -s PATH, --search_dir PATH
                        Where to search for the files. Must be an absolute path

optional arguments:
  -h, --help            show this help message and exit
  -b PATH, --bt_backup PATH
                        BT_backup location, defaults to:
                        Windows: C:\Users\<username>\AppData\Local\qBittorrent\BT_backup
                        Linux: /home/<username>/.local/share/data/qBittorrent/BT_backup
                        OS X: /Users/<username/Library/ApplicationSupport/qBittorrent/BT_backup
  -f N, --fix_duplicates N
                        Values:
                        0: throw an error when duplicates are found
                        1: be prompted to choose files when duplicates are found
                        2: use fuzzy string matching and choose files automatically
                        3: use fuzzy string matching and choose files automatically but be prompted before proceeding
                        Defaults to 0
  -d, --debug           Enable debug
```

Windows:
```
py qbit_automatch.py --hash HASH --search_dir SEARCH_DIR
```
Linux/OS X:
```
python3 qbit_automatch.py --hash HASH --search_dir SEARCH_DIR
```
* hash: Torrent hash. Can be obtained in qBittorrent UI by: Right Click Torrent -> Copy -> Hash  
* search_dir: the absolute path of the root folder of the files which are already on the disk  
* bt_backup: If your qBittorrent/BT_backup is not in the default location then you can use this parameter and input the correct absolute path  
* fix_duplicates: If the script is matching torrent files with more than one disk file you can use this option to fix it manually or use string matching to decide the correct file  

### What it does:
1. Opens the torrent file  
2. Searches the provided dir for matches in size and extension  
3. If all files have a match, updates qBittorrent <hash>.fastresume file with the new paths  
4. A <hash>.fastresume.bkp file will be created in the first run  

### Example:
Say you have this structure on your disk:  
```
D:
└── organized_folder
    ├── renamed_file_1.mkv
    └── renamed_file_2.avi
```
But you want to seed those files in a torrent that's organized like this:  
```
folder_1:
├── child_folder_1
│   └── file_1.mkv
└── child_folder_2
    └── child_folder_3
        └── file_2.avi
```
You'll get the torrent hash (let's say it's XPTO) and call the script like this: 
```
py qbit_automatch.py --hash XPTO --search_dir "D:\organized_folder"
```
or
```
py qbit_automatch.py --hash XPTO --search_dir "D:"
```
The script will automatically point the torrent to the proper folder and files.  
You still have to recheck the torrent in qbitorrent for now.  

