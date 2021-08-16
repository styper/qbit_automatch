import argparse
import os
import subprocess
import collections
from shutil import copyfile
from pathlib import Path

try:
    import bencode
except ModuleNotFoundError:
    raise SystemExit('Error: The bencode.py module is needed, you can install it with this command: pip install bencode.py')

def process_exists(process_name):
    call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
    # use buildin check_output right away
    output = subprocess.check_output(call).decode()
    # check in last line for process name
    last_line = output.strip().split('\r\n')[-1]
    # because Fail message could be translated
    return last_line.lower().startswith(process_name.lower())

def find_file(search_dir, file_length, file_extension, filename):
    os_root=os.path.basename(search_dir)
    for root, subdirs, files in os.walk(search_dir):
        for os_filename in files:
            os_file_extension = os.path.splitext(os_filename)[1]
            os_file_length=os.path.getsize(os.path.join(root, os_filename))
            if (file_length == os_file_length and
                file_extension == os_file_extension):
                os_relpath=os.path.relpath(root, search_dir)
                if os_relpath == '.':
                    return os.path.join(os_root, os_filename)
                else:
                    return os.path.join(os_root, os_relpath, os_filename)
    raise FileNotFoundError('File ' + filename + ' not found!')

#Parse input
parser=argparse.ArgumentParser()
parser.add_argument('--hash', help='Torrent hash')
parser.add_argument('--search_dir', help='Directory where the renamed files are')
parser.add_argument('--bt_backup', default=os.path.join(os.getenv('LOCALAPPDATA'), 'qBittorrent', 'BT_backup'), help='BT_backup location, defaults to: ' + os.path.join(os.getenv('LOCALAPPDATA')))
args=parser.parse_args()

#Validate input
if not os.path.isdir(args.search_dir):
    raise SystemExit('Error: ' + args.search_dir + ' is not a valid dir')

if not os.path.isdir(args.bt_backup):
    raise SystemExit('Error: ' + args.bt_backup + ' is not a valid dir')

qBt_savePath=str(Path(args.search_dir).parent.absolute())
bt_backup=args.bt_backup
mapped_files=[]
torrent_path=os.path.join(bt_backup, args.hash + '.torrent')
fastresume_path=os.path.join(bt_backup, args.hash + '.fastresume')
fastresume_bkp_path=fastresume_path + '.bkp'

print('hash..........: ' + args.hash)
print('search_dir....: ' + args.search_dir)
print('BT_backup.....: ' + bt_backup)
print('qBt_savePath..: ' + qBt_savePath)
print('torrent.......: ' + torrent_path)
print('fastresume....: ' + fastresume_path)
print('fastresume_bkp: ' + fastresume_bkp_path)

#Parse torrent file and search the lenghts and extension in the search_dir
with open(torrent_path, 'rb') as fd:
    torrent_data = bencode.decode(fd.read())
    for td_file in torrent_data['info']['files']:
        td_filename, td_file_extension = os.path.splitext(td_file['path'][-1])
        td_file_length=int(td_file['length'])
        found_file=find_file(args.search_dir, td_file_length, td_file_extension, td_filename)
        mapped_files.append(found_file)

#Check for duplicates
if len(mapped_files) != len(set(mapped_files)):
    #Uncomment to see files that were matched more than once
    #print([item for item, count in collections.Counter(mapped_files).items() if count > 1])
    raise SystemExit('Error: duplicates found, aborting')

#Fetch the fastresume file data
with open(fastresume_path, 'rb') as fd:
    fastresume_data = bencode.decode(fd.read())

fastresume_data_upd=fastresume_data.copy()
fastresume_data_upd['qBt-savePath']=qBt_savePath
fastresume_data_upd['save_path']=qBt_savePath
fastresume_data_upd['mapped_files']=mapped_files
if fastresume_data == fastresume_data_upd:
    print('Info: Fastresume data matches already, no changes made')
    exit(0)

if process_exists('qbittorrent.exe'):
    raise SystemExit('Error: qBittorrent is running, close it first')

#backup the original fastresume file if bkp doesnt exists
if not os.path.isfile(fastresume_bkp_path):
    copyfile(fastresume_path, fastresume_bkp_path)

with open(fastresume_path, 'wb') as fd:
    fd.write(bencode.encode(fastresume_data_upd))

print('Done')
