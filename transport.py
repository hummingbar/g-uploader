import os, threading, time
from pySmartDL import SmartDL
from googleapiclient.errors import HttpError
from apiclient import discovery
import oauth2client
from googleapiclient.http import MediaFileUpload
from oauth2client import client
from oauth2client import tools
import httplib2
from mimetypes import MimeTypes


class Flag:
    noauth_local_webserver = True
    logging_level = 'ERROR'


flags = Flag()
mime = MimeTypes()
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secrets.json'
APPLICATION_NAME = 'GDD'
CHUNKSIZE = 18 * 1024**2  # in MegaBytes, must be a multiple of 256 * 1024 bytes


class Manager(object):
    def __init__(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        credential_path = os.path.join(dir_path, 'drive-python-quickstart.json')
        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            credentials = tools.run_flow(flow, store, flags)
            print('Storing credentials to ' + credential_path)
        self.service = discovery.build('drive', 'v3', http=credentials.authorize(httplib2.Http()))
        self.download_arr = []
        self.upload_arr = []
        self.error_arr = []
        self.lock = threading.Lock()
        self.th1 = threading.Thread(target=self.checker)
        self.th1.setDaemon(True)
        self.th1.start()
        self.th2 = threading.Thread(target=self.uploader)
        self.th2.setDaemon(True)
        self.th2.start()

    def checker(self):
        while True:
            for obj in self.download_arr:
                if obj.isFinished():
                    self.download_arr.remove(obj)
                    if obj.isSuccessful():
                        obj.status = 'waiting for upload'
                        self.upload_arr.append(obj)
                    else:
                        self.error_arr.append(obj)
            time.sleep(0.66)

    def uploader(self):
        while True:
            if len(self.upload_arr) == 0:
                time.sleep(0.66)
                continue
            obj = self.upload_arr[0]
            obj.status = "uploading"
            file_metadata = {'name': os.path.basename(obj.dest)}

            media = MediaFileUpload(obj.dest,
                                    mimetype=mime.guess_type(os.path.basename(obj.dest))[0],
                                    chunksize=CHUNKSIZE,
                                    resumable=True)
            request = self.service.files().create(body=file_metadata,
                                                  media_body=media)
            response = None
            try:
                while response is None:
                    pretime = time.time()
                    status, response = request.next_chunk()
                    time_elapsed = time.time() - pretime
                    if status:
                        status.speed = '%.1f' % (CHUNKSIZE / 1024**2 / time_elapsed) + 'MB/s'
                        obj.up_status = status
            except HttpError as e:
                obj.errors.append(e)
                self.upload_arr.remove(obj)
                self.error_arr.append(obj)
                continue
            self.upload_arr.remove(obj)
            os.remove(obj.dest)

    def add_new_task(self, url, filename):
        dest = os.path.expanduser('~/Downloads/' + filename)
        obj = SmartDL(url, dest=dest, progress_bar=False, threads=1)
        obj.start(blocking=False)
        obj.filename = filename
        self.download_arr.append(obj)

    def status(self):
        res_down = []
        res_up = []
        res_err =[]
        for obj in self.download_arr:
            result = dict()
            result['filename'] = obj.filename
            result['speed'] = str(obj.get_speed(human=True))
            result['downloaded'] = str(obj.get_dl_size(human=True))
            result['fullsize'] = '%.1f' % (obj.filesize/1024.0**2)+" MB" if obj.filesize<1024**3 \
                else '%.3f' % (obj.filesize/1024.0**3)+" GB"
            result['eta'] = str(obj.get_eta(human=True))
            result['progress'] = '%.1f'%(obj.get_progress() * 100) + "%"
            result['formatedstring'] = \
                result['filename'] + " : " + \
                result['downloaded'] + " / " + \
                result['fullsize'] + " @ " + \
                result['speed'] + \
                " [" + result['progress'] + ", " + result['eta'] + "]"
            res_down.append(result)
        for obj in self.upload_arr:
            result = dict()
            result['formatedstring'] = obj.filename + " : " + obj.status
            if obj.status == 'uploading':
                if not hasattr(obj, 'up_status'):
                    result['formatedstring'] += " but is updating information"
                else:
                    result['formatedstring'] += " at %d%%" % int(obj.up_status.progress() * 100)
                    result['formatedstring'] += " @ " + obj.up_status.speed
                    result['formatedstring'] += " of " + ('%.1f' % (obj.up_status.total_size/1024.0**2)+" MB"
                                                          if obj.up_status.total_size<1024**3
                                                          else '%.1f' % (obj.up_status.total_size/1024.0**3)+" GB")
            res_up.append(result)
        for obj in self.error_arr:
            result = dict()
            result['formatedstring'] = obj.filename + " : " + obj.status + '\n'
            for e in obj.get_errors():
                result['formatedstring'] += str(e) + '\n'
            res_err.append(result)
        return res_down, res_up, res_err


if __name__ == "__main__":
    man = Manager()
    while True:
        string = input("Please specify command: s(status) or [link name]").strip()
        if string == 's':
            res_down, res_up, res_err = man.status()
            for x in res_down:
                print(x['formatedstring'])
            for x in res_up:
                print(x['formatedstring'])
        else:
            link = string[0:string.find(' ')]
            name = string[string.find(' ')+1:]
            man.add_new_task(link, name)