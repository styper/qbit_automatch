import os
import sys
import json
import argparse
import tempfile
from pathlib import Path
from shutil import copyfile
import bencode
import psutil
from rapidfuzz import process
from rapidfuzz.string_metric import levenshtein

class MyFile:
    def get_file_name(self):
        return os.path.basename(self.path)
    def get_extension(self):
        return os.path.splitext(self.path)[1]
    def __eq__(self, other):
        if isinstance(other, MyFile):
            if self.size == other.size and self.get_extension() == other.get_extension():
                return True
            return False
        return self == other

class JSONSerializable:
    def repr_json(self):
        raise NotImplementedError('You must implement this method.')
    def to_json(self):
        return json.dumps(self.repr_json())

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, JSONSerializable):
            return obj.repr_json()
        else:
            return json.JSONEncoder.default(self, obj)

class FileInTorrent(MyFile, JSONSerializable):
    def __init__(self, path, size):
        if type(path) == list:
            self.path = os.sep.join(path)
        else:
            self.path = path
        self.size = int(size)
        self.matches = []
    def set_single_match(self, match):
        self.matches.clear()
        self.matches.append(match)
    def get_match(self):
        return self.matches[0]
    def get_matches_count(self):
        return len(self.matches)
    def repr_json(self):
        return {'path':self.path, 'size':self.size, 'matches':self.matches}

class FileInDisk(MyFile, JSONSerializable):
    def __init__(self, **kwargs):
        if 'json' in kwargs:
            json_decoded = json.loads(kwargs['json'].rstrip())
            self.path = json_decoded['path']
            self.size = json_decoded['size']
        else:
            self.path = kwargs['path']
            self.size = int(kwargs['size'])
    def repr_json(self):
        return {'path':self.path, 'size':self.size}

class FastresumeFile(JSONSerializable):
    def __init__(self, bt_backup, hash, torrent_files):
        self.fastresume_path = os.path.join(bt_backup, hash + '.fastresume')
        self.fastresume_bkp_path = self.fastresume_path + '.bkp'
        self.mapped_files = []
        self.save_path = ''
        self.set_save_path(torrent_files)
        self.set_mapped_files(torrent_files)
    def set_mapped_files(self, torrent_files):
        for file_in_torrent in torrent_files.files:
            relpath=os.path.relpath(file_in_torrent.get_match().path, self.save_path)
            self.mapped_files.append(relpath)
    def set_save_path(self, torrent_files):
        self.save_path = str(Path(os.path.commonpath([x.get_match().path for x in torrent_files.files])).parent)
    def repr_json(self):
        return {'fastresume_path':self.fastresume_path, 'fastresume_bkp_path':self.fastresume_bkp_path, 'save_path':self.save_path, 'mapped_files':self.mapped_files}
    def update_fastresume(self):
        with open(self.fastresume_path, 'rb') as file_handle:
            fastresume_data = bencode.decode(file_handle.read())
        fastresume_data_upd=fastresume_data.copy()
        fastresume_data_upd['qBt-savePath']=self.save_path
        fastresume_data_upd['save_path']=self.save_path
        fastresume_data_upd['mapped_files']=self.mapped_files
        fastresume_data_upd['paused']=1
        if fastresume_data == fastresume_data_upd:
            print('INFO: Fastresume data matches already, no changes made')
            exit(0)
        if check_process_running('qbittorrent'):
            raise SystemExit('FATAL: qBittorrent is running, close it first')
        if not os.path.isfile(self.fastresume_bkp_path):
            copyfile(self.fastresume_path, self.fastresume_bkp_path)
        with open(self.fastresume_path, 'wb') as file_handle:
            file_handle.write(bencode.encode(fastresume_data_upd))

class TorrentFiles(JSONSerializable):
    THROW_ERROR = 0
    PROMPT = 1
    FUZZY_AUTO = 2
    FUZZY_PROMPT = 3
    def __init__(self, bt_backup, hash):
        self.torrent_path = os.path.join(bt_backup, hash + '.torrent')
        self.files = []
        with open(self.torrent_path, 'rb') as file_handle:
            torrent_data = bencode.decode(file_handle.read())
            if 'files' in torrent_data['info']:
                for td_file in torrent_data['info']['files']:
                    self.files.append(FileInTorrent(td_file['path'], td_file['length']))
            else:
                self.files.append(FileInTorrent(torrent_data['info']['name'], torrent_data['info']['length']))
    def check_unmatched(self):
        abort = False
        for file in self.files:
            if not file.matches:
                abort = True
                print('ERROR: File "' + file.path + '" has no matches')
        if abort: raise SystemExit('FATAL: This is script only works if all files are accounted for within the search_dir')
    def resolve_multiple(self, mode):
        dupicates_found = False
        for file_in_torrent in self.files:
            if file_in_torrent.get_matches_count() > 1:
                dupicates_found = True
                print('File "' + file_in_torrent.path + '" has the following duplicates:')
                options = []
                for seq_no, file_in_disk in enumerate(file_in_torrent.matches):
                    options.append(seq_no)
                    print(' [' + str(seq_no) + '] ' + file_in_disk.path)
                if mode == TorrentFiles.PROMPT:
                    user_input = ask_user('Select one', options, ret_type = 'int')
                    file_in_torrent.set_single_match(file_in_torrent.matches[user_input])
                elif mode in [TorrentFiles.FUZZY_AUTO, TorrentFiles.FUZZY_PROMPT]:
                    matches_filenames = [x.path for x in file_in_torrent.matches]
                    fuzzymatch = process.extractOne(file_in_torrent.path, matches_filenames, scorer=levenshtein)[0]
                    print(' Fuzzy match: ' + fuzzymatch)
                    file_in_torrent.set_single_match(next(x for x in file_in_torrent.matches if x.path == fuzzymatch))
        if dupicates_found and mode == TorrentFiles.THROW_ERROR:
            raise SystemExit('FATAL: duplicates found. This happens when 2 files have the same length and extension. You can run the script with --fix_duplicates to fix them. Check the help for possible values')
        elif dupicates_found and mode == TorrentFiles.FUZZY_PROMPT:
            if ask_user('Continue?', ['y', 'n']) == 'n':
                print('INFO: Exiting')
                exit(0)
    def check_duplicates(self):
        temp_list = []
        for file in self.files:
            temp_list.append(file.get_match().path)
        if len(temp_list) != len(set(temp_list)):
            return True
        return False
    def find_matches(self, search_dir):
        for file_in_torrent in self.files:
            search_dir.search_file(file_in_torrent)
    def repr_json(self):
        return {'torrent_path':self.torrent_path, 'files':self.files}

class SearchDir(JSONSerializable):
    def __init__(self, search_dir):
        self.search_dir = search_dir
        self.tempfile = tempfile.NamedTemporaryFile(prefix = 'pam', mode = "r+", newline = '\n')
        self.create_cache()
    def search_file(self, file_to_search):
        self.tempfile.seek(0, 0)
        line = self.tempfile.readline()
        while line:
            file_in_disk = FileInDisk(json=line)
            if (file_to_search == file_in_disk):
                file_to_search.matches.append(file_in_disk)
            line = self.tempfile.readline()
    def create_cache(self):
        for currdir, subdirs, files in os.walk(self.search_dir):
            for filename in files:
                file = FileInDisk(path = os.path.join(self.search_dir, currdir, filename), size = os.path.getsize(os.path.join(currdir, filename)))
                self.tempfile.write(file.to_json() + '\n')
    def repr_json(self):
        return {'search_dir':self.search_dir, 'tempfile':self.tempfile.name}

class ReadablePath(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        input_path=values
        if not os.path.isdir(input_path):
            raise SystemExit('FATAL: "' + input_path + '" is not a valid path')
        if not os.access(input_path, os.R_OK):
            raise SystemExit('FATAL: "' + input_path + '" is not readable')
        input_path = os.path.abspath(input_path)
        setattr(namespace,self.dest,input_path)

class SHA1Hash(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        input_hash=values
        if len(input_hash) != 40:
            raise SystemExit('FATAL: "' + input_hash + '" is not a valid hash, check --help')
        try:
            sha_int = int(input_hash, 16)
        except ValueError:
            raise SystemExit('FATAL: "' + input_hash + '" is not a valid hash, check --help')
        setattr(namespace,self.dest,input_hash)

def ask_user(question, options, ret_type = 'str'):
    options = list(map(str, options))
    response = ''
    while response.lower() not in options:
        response = input(question + ' (' + '/'.join(options) + '): ')
    if ret_type == 'int':
        return int(response)
    return response

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

def get_bt_backup_default():
    if sys.platform == "win32":
        return os.path.join(os.getenv('LOCALAPPDATA'), 'qBittorrent', 'BT_backup')
    elif sys.platform == "linux":
        return os.path.join(Path.home(), '.local', 'share', 'data', 'qBittorrent', 'BT_backup')
    elif sys.platform == "darwin":
        return os.path.join(Path.home(), 'Library', 'ApplicationSupport', 'qBittorrent', 'BT_backup')

def parse_input():
    parser=argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    optional = parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    parser._action_groups.append(optional)
    required.add_argument('-a', '--hash', action=SHA1Hash, help='Torrent hash. In qBittorrent right click the torrent -> copy -> hash', required=True)
    required.add_argument('-s', '--search_dir', metavar='PATH', action=ReadablePath, help='Where to search for the files. Must be an absolute path', required=True)
    optional.add_argument('-b', '--bt_backup', metavar='PATH', default=get_bt_backup_default(), action=ReadablePath, help='BT_backup location, defaults to:\nWindows: C:\\Users\\<username>\\AppData\\Local\\qBittorrent\\BT_backup\nLinux: /home/<username>/.local/share/data/qBittorrent/BT_backup\nOS X: /Users/<username/Library/ApplicationSupport/qBittorrent/BT_backup')
    optional.add_argument('-f', '--fix_duplicates', metavar='N', default=0, type=int, choices=range(0, 4), help='Values:\n0: throw an error when duplicates are found\n1: be prompted to choose files when duplicates are found\n2: use fuzzy string matching and choose files automatically\n3: use fuzzy string matching and choose files automatically but be prompted before proceeding\nDefaults to 0')
    optional.add_argument('-d', '--debug', action='store_true', help='Enable debug')
    return parser.parse_args()

def check_python_version():
    if (sys.version_info < (2, 7) or (3, 0) <= sys.version_info < (3, 2)):
        raise SystemExit('FATAL: Python 2.7 or 3.2 is required')

def main():
    check_python_version()
    input_args = parse_input()
    try:
        if input_args.debug:
            print('DEBUG: input_args:' + json.dumps(vars(input_args), cls=ComplexEncoder, indent = 2))
            print('DEBUG: Opening search dir and creating cache in tempfile')
        search_dir = SearchDir(input_args.search_dir)

        if input_args.debug:
            print('DEBUG: search_dir:' + json.dumps(search_dir, cls=ComplexEncoder, indent = 2))
            print('DEBUG: Opening torrent file')
        torrent_files = TorrentFiles(input_args.bt_backup, input_args.hash)

        if input_args.debug:
            print('DEBUG: torrent_files:' + json.dumps(torrent_files, cls=ComplexEncoder, indent = 2))
            print('DEBUG: Finding matches')
        torrent_files.find_matches(search_dir)

        if input_args.debug:
            print('DEBUG: After matches search')
            print('DEBUG: torrent_files:' + json.dumps(torrent_files, cls=ComplexEncoder, indent = 2))
            print('DEBUG: Checking if files have no matches')
        torrent_files.check_unmatched()

        if input_args.debug:
            print('DEBUG: Checking for multiple matches')
        torrent_files.resolve_multiple(input_args.fix_duplicates)

        if input_args.debug:
            print('DEBUG: After multiple matches check')
            print('DEBUG: torrent_files:' + json.dumps(torrent_files, cls=ComplexEncoder, indent = 2))
            print('DEBUG: Checking if two torrent files point to the same disk file')
        torrent_files.check_duplicates()

        if input_args.debug:
            print('DEBUG: Finished checking files')
        fastresume_file = FastresumeFile(input_args.bt_backup, input_args.hash, torrent_files)

        if input_args.debug:
            print('DEBUG: fastresume_file:' + json.dumps(fastresume_file, cls=ComplexEncoder, indent = 2))
            print('DEBUG: Updating fastresume file')
        fastresume_file.update_fastresume()

        print('INFO: Done')
    finally:
        try:
            search_dir.tempfile.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
