# qbit_automatch

### Description:
Script to match torrent files with renamed files, then updating qBittorrent accordingly.  
This script is currently Windows dependent because it uses TASKLIST to check if qbittorrent.exe is running. Should be easy to adapt though.  
The script uses length in bytes and extension to match the files, torrent files don't have individual file hashes so this is what I could do.  

### Usage:
qbit_automatch.py --hash HASH --search_dir SEARCH_DIR  
Where hash is the torrent hash. Can be obtained in qBittorrent UI by: Right Click Torrent -> Copy -> Hash  
Search_dir is the root of the file which is already on the disk.  
If BT_backup is not in the default location (%LOCALAPPDATA%\qBittorrent\BT_backup) then you can use the parameter --bt_backup and pass the correct path  

### What it does:
Opens the torrent file  
Searches the provided dir for matches in size and extension  
If all files have a match, updates qBittorrent with the new location and filenames  
A fastresume bkp file will be saved for the first run  

### Example:
Say you have this structure on your disk:  
D:\organized_folder  
  --renamed_file_1.mkv  
  --renamed_file_2.avi  
But you want to seed those files in a torrent that's organized like this:  
folder_1  
--child_folder_2  
  --file_1.mkv  
--child_folder_3  
  --child_folder_4  
    --file_2.avi  
You'll get the torrent hash (let's say it's XPTO) and call the script like this:  
qbit_automatch.py --hash XPTO --search_dir "D:\organized_folder"  
The script will automacally point the torrent to the proper folder and files.  
You still have to recheck the torrent in qbitorrent for now.  

