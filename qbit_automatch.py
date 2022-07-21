import argparse
import os
import collections
import sys
from shutil import copyfile
from pathlib import Path

try:
    import bencode
except ModuleNotFoundError:
    raise SystemExit('Error: The bencode.py module is needed, you can install it with this command: python -m pip install bencode.py')

try:
    import psutil
except ModuleNotFoundError:
    raise SystemExit('Error: The psutil module is needed, you can install it with this command: python -m pip install psutil')

try:
    from rapidfuzz import process
    from rapidfuzz.string_metric import levenshtein
except ModuleNotFoundError:
    raise SystemExit('Error: The rapidfuzz module is needed, you can install it with this command: python -m pip install rapidfuzz')

def get_bt_backup_default():
    if sys.platform == "win32":
        return os.path.join(os.getenv('LOCALAPPDATA'), 'qBittorrent', 'BT_backup')
    elif sys.platform == "linux":
        return os.path.join(Path.home(), '.local', 'share', 'data', 'qBittorrent', 'BT_backup')
    elif sys.platform == "darwin":
        return os.path.join(Path.home(), 'Library', 'ApplicationSupport', 'qBittorrent', 'BT_backup')

def check_process_running(processName):
     #Iterate over the all the running process
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False;

def yes_or_no(question):
    reply = str(input(question+' (y/n): ')).lower().strip()
    if reply[0] == 'y':
        return True
    if reply[0] == 'n':
        return False
    else:
        return yes_or_no(question)

def cache_search_dir(search_dir):
    search_dir_cache=[]
    for root, subdirs, files in os.walk(search_dir):
        for os_filename in files:
            os_file_extension = os.path.splitext(os_filename)[1]
            os_file_length=os.path.getsize(os.path.join(root, os_filename))
            os_relpath=os.path.relpath(root, search_dir)
            search_dir_cache.append({'absolute_path':os.path.join(search_dir, root, os_filename), 'extension':os_file_extension, 'length':os_file_length})
    return search_dir_cache

def find_file(search_dir_cache, file_length, file_extension, filename):
    files=[]
    for i in search_dir_cache:
        if (file_length == i['length'] and
            file_extension == i['extension']):
            files.append(i['absolute_path'])
    return files

def update_fastresume(qBt_savePath, mapped_files):
    #Fetch the fastresume file data
    with open(fastresume_path, 'rb') as fd:
        fastresume_data = bencode.decode(fd.read())
    #update the root save path and files
    fastresume_data_upd=fastresume_data.copy()
    fastresume_data_upd['qBt-savePath']=qBt_savePath
    fastresume_data_upd['save_path']=qBt_savePath
    fastresume_data_upd['mapped_files']=mapped_files
    fastresume_data_upd['paused']=1
    if fastresume_data == fastresume_data_upd:
        print('Info: Fastresume data matches already, no changes made')
        exit(0)
    if check_process_running('qbittorrent'):
        raise SystemExit('Error: qBittorrent is running, close it first')
    #backup the original fastresume file if bkp doesnt exists
    if not os.path.isfile(fastresume_bkp_path):
        copyfile(fastresume_path, fastresume_bkp_path)
    #write the changed file to disk
    with open(fastresume_path, 'wb') as fd:
        fd.write(bencode.encode(fastresume_data_upd))

def rename_files(searched_files):
    for file in input:
        file_to_change = file["result"][0]
        file_to_change_name = file_to_change.split("\\")[-1:][0]
        file_location = file_to_change.replace(file_to_change_name,"")
        file_new_name = file_location + file["searched"]
        os.rename(f"{file_to_change}",f"{file_new_name}")
    #todo1 - update the fast resume data after files are renamed so that file doesnt need to be rechecked.
    #todo2 - rename parent folder also where required.
    
parser=argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
optional = parser._action_groups.pop()
required = parser.add_argument_group('required arguments')
parser._action_groups.append(optional)
required.add_argument('-a', '--hash', help='Torrent hash. In qBittorrent right click the torrent -> copy -> hash', required=True)
required.add_argument('-s', '--search_dir', metavar='PATH', help='Where to search for the files. Must be an absolute path', required=True)
optional.add_argument('-b', '--bt_backup', metavar='PATH', default=get_bt_backup_default(), help='BT_backup location, defaults to:\nWindows: C:\\Users\\<username>\\AppData\\Local\\qBittorrent\\BT_backup\nLinux: /home/<username>/.local/share/data/qBittorrent/BT_backup\nOS X: /Users/<username/Library/ApplicationSupport/qBittorrent/BT_backup')
optional.add_argument('-f', '--fix_duplicates', metavar='N', default=0, help='Values:\n0: throw an error when duplicates are found\n1: be prompted to choose files when duplicates are found\n2: use fuzzy string matching and choose files automatically\n3: use fuzzy string matching and choose files automatically but be prompted before proceeding\nDefaults to 0')
optional.add_argument('-d', '--debug', action='store_true', help='Enable debug')
args=parser.parse_args()

#Validate input
if not os.path.isdir(args.search_dir):
    raise SystemExit('Error: ' + args.search_dir + ' is not a valid dir')

if not os.path.isdir(args.bt_backup):
    raise SystemExit('Error: ' + args.bt_backup + ' is not a valid dir. Try calling the script with --bt_backup parameter and the correct path')

bt_backup=args.bt_backup
torrent_path=os.path.join(bt_backup, args.hash + '.torrent')
fastresume_path=os.path.join(bt_backup, args.hash + '.fastresume')
fastresume_bkp_path=fastresume_path + '.bkp'

if args.debug: print('hash..........: ' + args.hash)
if args.debug: print('search_dir....: ' + args.search_dir)
if args.debug: print('BT_backup.....: ' + bt_backup)
if args.debug: print('torrent.......: ' + torrent_path)
if args.debug: print('fastresume....: ' + fastresume_path)
if args.debug: print('fastresume_bkp: ' + fastresume_bkp_path)

#Cache the search_dir
search_dir_cache=cache_search_dir(args.search_dir)

#Parse torrent file and search the lenghts and extension in the search_dir
searched_files=[]
with open(torrent_path, 'rb') as fd:
    torrent_data = bencode.decode(fd.read())
    for td_file in torrent_data['info']['files']:
        td_filename, td_file_extension = os.path.splitext(td_file['path'][-1])
        td_file_length=int(td_file['length'])
        result=find_file(search_dir_cache, td_file_length, td_file_extension, td_file['path'][-1])
        searched_files.append({'searched':os.sep.join(td_file['path']), 'result':result})

#Check if some files haven't been found
not_found_abort=False
for i in searched_files:
    if not i['result']:
        print('File not found: ' + i['searched'])
        not_found_abort=True
if not_found_abort:
    raise SystemExit('Error: This is script only works if all files are accounted for within the search_dir')

#Check if a file has duplicates
duplicate_abort=False
for i in searched_files:
    if len(i['result']) > 1:
        if args.fix_duplicates == '1':
            print('File "' + i['searched'] + '" has the following duplicates. Input which is the correct one by entering the number:')
        else:
            print('File "' + i['searched'] + '" has the following duplicates:')
        for idx, val in enumerate(i['result']):
            print(' [' + str(idx) + '] ' + val)
            duplicate_abort=True
        if args.fix_duplicates in ['2','3']:
            cache_result=process.extractOne(i['searched'], i['result'], scorer=levenshtein)[0]
            i['result'] = []
            i['result'].append(cache_result)
            print('Fuzzy match: ' + cache_result)
        elif args.fix_duplicates == '1':
            while True:
                try:
                    user_input=int(input("Enter your value: "))
                    cache_result=i['result'][user_input]
                    i['result'] = []
                    i['result'].append(cache_result)
                    break
                except (IndexError,TypeError,ValueError) as e:
                    pass
if duplicate_abort and args.fix_duplicates not in ['1','2','3']:
    raise SystemExit('Error: duplicates found. This happens when 2 files have the same length and extension. You can run the script with --fix_duplicates to fix them. Check the help for possible values')
if duplicate_abort and args.fix_duplicates in ['3']:
    if not yes_or_no('Continue?'):
        exit(0)

#extract the paths
searched_paths=[]
for i in searched_files:
    searched_paths.append(i['result'][0])

if len(searched_paths) != len(set(searched_paths)):
    raise SystemExit('Error: There are duplicates in the values')

print('All files matched')

#Get the common path of all files and set the mapped_files as the relative path to the common path
mapped_files=[]
qBt_savePath=str(Path(os.path.commonpath(searched_paths)).parent)
for file_path in searched_paths:
    relpath=os.path.relpath(file_path, qBt_savePath)
    mapped_files.append(relpath)

if args.debug: print('qBt_savePath..: ' + qBt_savePath)

files_or_fastresume = input("(1) Rename Files\n(2) Update fast resume data\n\nSelection:")

#if rename files option is selected rename files
if files_or_fastresume == "1":
    rename_files(searched_files)
    print("all files renamed")
    
#If update fast resume is selected, Updates qBittorrent fastresume file
elif files_or_fastresume == "2":
    update_fastresume(qBt_savePath, mapped_files)
    print('Updated fastresume file')

else:
    print("incorrect selection")    

    print('Done')
