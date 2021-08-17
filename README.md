# qbit_automatch

### Description:
Script to match torrent files with renamed files, then updating qBittorrent accordingly.  
The script uses length in bytes and extension to match the files, torrent files don't have individual file hashes so this is what I could do.  

### Dependencies:

[bencode.py](https://github.com/fuzeman/bencode.py)  
[psutil](https://github.com/giampaolo/psutil)  

```
python -m pip install bencode.py psutil
```
or
```
python3 -m pip install bencode.py psutil
```
or
```
pip install bencode.py psutil
```

### Usage:
```
usage: qbit_automatch.py [-h] [--hash HASH] [--search_dir SEARCH_DIR] [--bt_backup BT_BACKUP]

optional arguments:
  -h, --help            show this help message and exit
  --hash HASH           Torrent hash
  --search_dir SEARCH_DIR
                        Directory where the renamed files are
  --bt_backup BT_BACKUP
                        BT_backup location, defaults to: C:\Users\Erick\AppData\Local\qBittorrent\BT_backup
```

Windows:
```
py qbit_automatch.py --hash HASH --search_dir SEARCH_DIR
```
Linux/OS X:
```
python3 qbit_automatch.py --hash HASH --search_dir SEARCH_DIR
```
hash: Torrent hash. Can be obtained in qBittorrent UI by: Right Click Torrent -> Copy -> Hash  
search_dir: the absolute path of the root folder of the files which are already on the disk  
bt_backup: If your qBittorrent/BT_backup is not in the default location then you can use the parameter --bt_backup and pass the correct absolute path  

### What it does:
Opens the torrent file  
Searches the provided dir for matches in size and extension  
If all files have a match, updates qBittorrent <hash>.fastresume file with the new paths  
A <hash>.fastresume.bkp file will be created in the first run  

### Example:
Say you have this structure on your disk:  
```
D:\organized_folder  
    --renamed_file_1.mkv  
    --renamed_file_2.avi  
```
But you want to seed those files in a torrent that's organized like this:  
```
folder_1  
  --child_folder_2  
    --file_1.mkv  
  --child_folder_3  
    --child_folder_4  
      --file_2.avi  
```
You'll get the torrent hash (let's say it's XPTO) and call the script like this: 
```
py qbit_automatch.py --hash XPTO --search_dir "D:\organized_folder"
```
The script will automatically point the torrent to the proper folder and files.  
You still have to recheck the torrent in qbitorrent for now.  

