import paramiko
import os
import frappe
from csf_tz.stanbic.xml import parse_xml


class Paramiko:
    def __init__(self, hostname, user, key_path, port=22):
        self.hostname = hostname
        self.user = user
        self.port = port
        self.key_path = key_path
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect()

    def connect(self):
        print("Connecting to the server")
        pkey = paramiko.RSAKey.from_private_key_file(self.key_path)
        self.client.connect(
            self.hostname,
            port=self.port,
            username=self.user,
            pkey=pkey,
            look_for_keys=False,
            disabled_algorithms={"pubkeys": ["rsa-sha2-512", "rsa-sha2-256"]},
            timeout=100,
        )
        print("Connected to the server")

    def download(self, remote_path, local_path, cleanup=False):
        create_dir_if_not_exists(local_path)
        try:
            sftp = self.client.open_sftp()
            print("Connected to the sftp server")
            rfiles = sftp.listdir(remote_path)
            rfile = ""
            for rfile in rfiles:
                sftp.get(remote_path + "/" + rfile, local_path + "/" + rfile)
                print(
                    f"Downloaded the file {rfile} from the remote folder {remote_path} to the local folder {local_path}"
                )
                if cleanup:
                    sftp.remove(remote_path + "/" + rfile)
                    print(f"Removing the files from the remote folder: {rfile}")
            sftp.close()
        except Exception as e:
            frappe.throw(str(e))
        # return list of names of the files downloaded
        return os.listdir(local_path)

    def upload(self, local_path, remote_path, cleanup=False):
        create_dir_if_not_exists(local_path)
        try:
            sftp = self.client.open_sftp()
            print("Connected to the sftp server")
            lfiles = os.listdir(local_path)
            lfile = ""
            for lfile in lfiles:
                sftp.put(local_path + "/" + lfile, remote_path + "/" + lfile)
                print(
                    f"Uploaded the file {lfile} to the local folder {local_path} from the remote folder {remote_path}"
                )
                if cleanup:
                    os.remove(local_path + "/" + lfile)
                    print(f"Removing the files from the remote folder: {lfile}")
            sftp.close()
        except Exception as e:
            frappe.throw(str(e))
        # return list of names of the files uploaded
        return lfiles

    def close(self):
        self.client.close()
        print("Connection closed")

    def execute(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        print("Executing the command")
        return stdout.read().decode("utf-8"), stderr.read().decode("utf-8")


def create_dir_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_site_path():
    return frappe.get_site_path("private", "files")


def get_local_path(folders_name=[]):
    path = get_absolute_path("/" + "/".join(folders_name))
    return path


def download_stanbank_files(settings_name):
    # get the files from the stanbic remote folder
    # download the files to the local folder

    # get the remote path
    remote_path = "/Inbox"
    # get the local path
    local_path = get_local_path(["private", "files", "stanbic", "inbox"])

    # get the settings
    settings = frappe.get_cached_doc("Stanbic Setting", settings_name)

    key_file_path = get_absolute_path(settings.private_key)
    print("key_file_path", key_file_path)

    # create the paramiko object
    paramiko_obj = Paramiko(
        settings.sftp_url, settings.sftp_user, key_file_path, settings.port
    )

    # download the files
    files = paramiko_obj.download(remote_path, local_path, cleanup=True)

    # close the connection
    paramiko_obj.close()

    return files


def upload_stanbank_files(settings_name):
    # get the files from the local folder
    # upload the files to the stanbic remot folder

    # get the remote path
    remote_path = "/Outbox"

    # get the local path
    local_path = get_local_path(["private", "files", "stanbic", "outbox"])

    # get the settings
    settings = frappe.get_cached_doc("Stanbic Setting", settings_name)

    key_file_path = get_absolute_path(settings.private_key)
    print("key_file_path", key_file_path)

    # create the paramiko object
    paramiko_obj = Paramiko(
        settings.sftp_url, settings.sftp_user, key_file_path, settings.port
    )

    # upload the files
    files = paramiko_obj.upload(local_path, remote_path, cleanup=True)

    # close the connection
    paramiko_obj.close()

    return files


def sync_stanbank_files(settings_name, is_test=False):
    # upload the files to the stanbic remot folder
    # get the files from the stanbic remot folder
    # download the files to the local folder

    # upload the files
    upload_files = upload_stanbank_files(settings_name)

    # download the files
    download_files = download_stanbank_files(settings_name)

    return upload_files, download_files


def sync_all_stanbank_files():
    # get all the settings
    settings = frappe.get_all("Stanbic Setting", filters={"enabled": 1})
    for setting in settings:
        sync_stanbank_files(setting.name, setting.is_test)


def get_absolute_path(file_path):
    from frappe.utils import cstr

    site_name = cstr(frappe.local.site)
    bench_path = frappe.utils.get_bench_path()

    if file_path.startswith("/files/"):
        return bench_path + "/sites/" + site_name + "/public/" + file_path
    elif file_path.startswith("/private/files/"):
        return bench_path + "/sites/" + site_name + file_path

    else:
        return file_path


def process_download_files():
    inbox_file_path = get_local_path(["private", "files", "stanbic", "inbox"])
    os.makedirs(os.path.dirname(inbox_file_path), exist_ok=True)
    inbox_files_list = os.listdir(inbox_file_path)
    for file in inbox_files_list:
        doc_changed = 0
        try:
            if file.endswith(".xml"):
                if "ACK" in file or "INTAUD" in file or "FINAUD" in file:
                    path = get_local_path(
                        ["private", "files", "stanbic", "inbox", file]
                    )

                    file_dict = parse_xml(path)
                    file_json = frappe.as_json(file_dict)
                    print("filename", path)
                    pain_doc_name = file_dict["Document"]["CstmrPmtStsRpt"][
                        "OrgnlGrpInfAndSts"
                    ]["OrgnlMsgId"]
                    pain_doc = frappe.get_doc(
                        "Stanbic Payments Initiation", pain_doc_name
                    )
                    if "ACK" in file and not pain_doc.stanbic_ack:
                        pain_doc.stanbic_ack = file_json
                        pain_doc.stanbic_ack_change = 1
                        doc_changed = 1
                    elif "INTAUD" in file and not pain_doc.stanbic_intaud:
                        pain_doc.stanbic_intaud = file_json
                        pain_doc.stanbic_intaud_change = 1
                        doc_changed = 1
                    elif "FINAUD" in file and not pain_doc.stanbic_finaud:
                        pain_doc.stanbic_finaud = file_json
                        pain_doc.stanbic_finaud_change = 1
                        doc_changed = 1
        except Exception as e:
            print("Error processing the file", file, str(e))
        if doc_changed:
            pain_doc.save()
