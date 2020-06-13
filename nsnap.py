#!/usr/bin/env python3

#
# version 1.0
# https://github.com/ethbian/nsnap
#

import os
import logging
import datetime
import subprocess
import xmltodict
import sqlite3

# ---------------------------------------------------- check these
DBDIR = '/var/lib/nsnap'
DBFILE = 'nsnap.sqlite3'
NMAP_DIR = '/var/lib/nsnap/scans'
LOG_FILE = '/var/log/nsnap.log'
NMAP_TARGET = '192.168.201.22-24'
NMAP_OPTS = ['-sT']

NMAP_PATH = '/usr/bin/nmap'
NDIFF_PATH = '/usr/bin/ndiff'
DBPATH = '{}/{}'.format(DBDIR, DBFILE)

# ---------------------------------------------------- db schema
CREATE_TABLE_HOSTS = '''CREATE TABLE IF NOT EXISTS hosts (
    id INTEGER PRIMARY KEY,
    ip text NOT NULL,
    name text,
    UNIQUE(ip)
);'''
CREATE_INDEX_HOSTS_IP = 'CREATE INDEX hosts_ip_idx ON hosts(ip);'
CREATE_TABLE_FULLSCAN = '''CREATE TABLE IF NOT EXISTS fullscan (
    id INTEGER NOT NULL,
    updated INTEGER NOT NULL,
    port INTEGER NOT NULL,
    protocol TEXT NOT NULL,
    state TEXT NOT NULL,
    service TEXT,
    FOREIGN KEY(id) REFERENCES hosts(id)
    );'''
CREATE_INDEX_FULLSCAN_UPDATED = 'CREATE INDEX fullscan_updated_idx ON fullscan(updated);'
CREATE_INDEX_FULLSCAN_ID_UPDATED = 'CREATE INDEX fullscan_id_updated_idx ON fullscan(id, updated);'

CREATE_TABLE_DIFFSCAN = '''CREATE TABLE IF NOT EXISTS diffscan (
    id INTEGER NOT NULL,
    updated INTEGER NOT NULL,
    diff TEXT NOT NULL,
    comment TEXT NULL,
    FOREIGN KEY(id) REFERENCES hosts(id)
);'''
CREATE_INDEX_DIFFSCAN_UPDATED = 'CREATE INDEX diffscan_updated_idx ON diffscan(updated);'
CREATE_INDEX_DIFFSCAN_ID_UPDATED = 'CREATE INDEX diffscan_id_updated_idx ON diffscan(id, updated);'


# ---------------------------------------------------- DB class
class DB:
    def __init__(self):
        self.dbconn = sqlite3.connect(DBPATH)
        self.dbcursor = self.dbconn.cursor()

    def create_tables(self):
        self.dbcursor.execute(CREATE_TABLE_HOSTS)
        self.dbcursor.execute(CREATE_INDEX_HOSTS_IP)
        self.dbcursor.execute(CREATE_TABLE_FULLSCAN)
        self.dbcursor.execute(CREATE_INDEX_FULLSCAN_UPDATED)
        self.dbcursor.execute(CREATE_INDEX_FULLSCAN_ID_UPDATED)
        self.dbcursor.execute(CREATE_TABLE_DIFFSCAN)
        self.dbcursor.execute(CREATE_INDEX_DIFFSCAN_UPDATED)
        self.dbcursor.execute(CREATE_INDEX_DIFFSCAN_ID_UPDATED)
        self.dbconn.commit()

    def insert_hostip(self, hostip):
        sql = 'INSERT OR IGNORE INTO hosts(ip) VALUES("{}");'.format(hostip)
        try:
            self.dbcursor.execute(sql)
        except Exception as ex:
            logging.warning('cannot add new host: {}: {}'.format(hostip, ex))

    def update_hostname(self, hostip, hostname):
        sql = 'UPDATE hosts SET name="{}" WHERE ip="{}"'.format(hostname, hostip)
        try:
            self.dbcursor.execute(sql)
        except Exception as ex:
            logging.warning('cannot update host {} with name {}: {}'.format(hostip, hostname, ex))

    def select_id_by_ip(self, hostip):
        hostid = 0
        sql = 'SELECT id FROM hosts WHERE ip="{}";'.format(hostip)
        try:
            self.dbcursor.execute(sql)
        except Exception as ex:
            logging.warning('error getting id by ip: {}'.format(ex))
        else:
            rows = self.dbcursor.fetchone()
            if rows is not None:
                hostid = rows[0]
        return hostid

    def update_service(self, hostid, timestamp, service):
        sql = 'INSERT INTO fullscan VALUES({}, {}, {}, "{}", "{}", "{}");'.format(hostid, timestamp, service['port'], service['proto'], service['state'], service['service'])
        try:
            self.dbcursor.execute(sql)
        except Exception as ex:
            logging.error('error inserting fullscan result: {}: {}'.format(ex, sql))

    def update_diff(self, hostid, timestamp, scan_diff):
        sql = 'INSERT INTO diffscan VALUES({}, {}, "{}", "");'.format(hostid, timestamp, scan_diff)
        try:
            self.dbcursor.execute(sql)
        except Exception as ex:
            logging.error('error inserting diffscan result: {}: {}'.format(ex, sql))

    def dbcommit(self):
        self.dbconn.commit()

    def dbclose(self):
        self.dbconn.close()


# ----------------------------------------------------- main
# ---------------------------------------------------- logging
logging.basicConfig(filename=LOG_FILE, filemode='a', level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())
logging.info('\n*** Log file: {}\n'.format(LOG_FILE))

if not os.path.exists(NMAP_PATH):
    raise SystemExit('Cannot find nmap: {} does not exist'.format(NMAP_PATH))
if not os.path.exists(NMAP_DIR):
    raise SystemExit('Result directory: {} does not exist'.format(NMAP_DIR))
try:
    os.chdir(NMAP_DIR)
except Exception as ex:
    raise SystemExit('Cannot change directory to {}: {}'.format(NMAP_DIR, ex))


# ---------------------------------------------------- nmap
logging.info('*** Starting nmap scan: {}\n'.format(datetime.datetime.now()))
scan_time = datetime.datetime.now()
NMAP_FILE = 'scan_{}.xml'.format(scan_time.strftime('%Y%m%d-%H%M%S'))
LAST_FILE = 'last'
logging.info('    {} saving results to {}'.format(scan_time, NMAP_FILE))

NMAP_EXEC = [NMAP_PATH, '-Pn', '-v0', '-oX']
NMAP_EXEC.append(NMAP_FILE)
NMAP_EXEC += NMAP_OPTS
NMAP_EXEC.append(NMAP_TARGET)

result = subprocess.call(NMAP_EXEC)
if result != 0:
    raise SystemExit('nmap scan failed')
logging.info('\n*** Nmap scan finished: {}\n'.format(datetime.datetime.now()))


# ---------------------------------------------------- db check & create
if not os.path.exists(DBDIR):
    raise SystemExit('Snapshotter directory: {} does not exist'.format(DBDIR))
if not os.path.exists(DBPATH):
    logging.warning('*** DB does not exist, creating...')
    try:
        db = DB()
        db.create_tables()
    except Exception as ex:
        if os.path.exists(DBPATH):
            os.remove(DBPATH)
        raise SystemExit('Cannot create db (check directory rights): {}'.format(ex))
    else:
        db.dbclose()


# ---------------------------------------------------- db connect
try:
    db = DB()
except Exception as ex:
    raise SystemExit('Cannot connect to DB: {}'.format(ex))
now = int(datetime.datetime.timestamp(datetime.datetime.now()))


# ---------------------------------------------------- full scan
with open(NMAP_FILE) as xml_file:
    nmap_result = xmltodict.parse(xml_file.read())
xml_file.close()

for entry in nmap_result['nmaprun']['host']:
    target_ip = entry['address'].get('@addr', 'n/a')

    if isinstance(entry['hostnames'], dict):
        target_name = entry['hostnames']['hostname']['@name']
    else:
        target_name = '-'

    target_services = []

    if 'port' in entry['ports'].keys():
        if isinstance(entry['ports']['port'], dict):
            target_proto = entry['ports']['port']['@protocol']
            target_port = entry['ports']['port']['@portid']
            target_state = entry['ports']['port']['state']['@state']
            target_service = entry['ports']['port']['service']['@name']
            target_services.append({'proto': target_proto, 'port': target_port, 'state': target_state, 'service': target_service})
        elif isinstance(entry['ports']['port'], list):
            for entry_ports in entry['ports']['port']:
                target_proto = entry_ports['@protocol']
                target_port = entry_ports['@portid']
                target_state = entry_ports['state']['@state']
                target_service = entry_ports['service']['@name']
                target_services.append({'proto': target_proto, 'port': target_port, 'state': target_state, 'service': target_service})

    if len(target_services) == 0:
        continue

    logging.info('    {}:{}'.format(target_ip, target_name))
    db.insert_hostip(target_ip)
    db.update_hostname(target_ip, target_name)
    ip_id = db.select_id_by_ip(target_ip)
    if ip_id != 0 and len(target_services) > 0:
        for service in target_services:
            db.update_service(ip_id, now, service)
db.dbcommit()

if not os.path.exists(LAST_FILE):
    logging.warning('Previous scan results file does not exist (is this your first scan?)')
    try:
        os.symlink(NMAP_FILE, LAST_FILE)
    except Exception as ex:
        logging.warning('Cannot create link to the last(current) scan results file: {}'.format(ex))
else:
    # ---------------------------------------------------- diff scan
    DIFFSCAN_FILE = 'diff_{}.out'.format(scan_time.strftime('%Y%m%d-%H%M%S'))
    try:
        DIFFSCAN_OPEN = open(DIFFSCAN_FILE, 'w')
    except Exception as ex:
        raise SystemExit('Cannot create diffscan file: {}'.format(ex))
    result = subprocess.call([NDIFF_PATH, LAST_FILE, NMAP_FILE], stdout=DIFFSCAN_OPEN)
    DIFFSCAN_OPEN.close()

    try:
        os.remove(LAST_FILE)
    except Exception as ex:
        logging.warning('Cannot remove last symlink: {}'.format(ex))
    try:
        os.symlink(NMAP_FILE, LAST_FILE)
    except Exception as ex:
        logging.warning('Cannot create last scan results file symlink: {}'.format(ex))

    if result == 0:
        logging.info('\n    No differences detected. Done.')
    elif result != 1:
        raise SystemExit('Cannot create ndiff file, skipping {}.'.format(result))
    else:
        target_ip = ''
        scan_diff = ''

        with open(DIFFSCAN_FILE) as diff_file:
            total_updated = 0
            for line in diff_file:
                if line.startswith('+Nmap') or line.startswith('-Nmap')\
                    or line.startswith('+Not shown') or line.startswith('-Not shown')\
                        or line.startswith(' PORT'):
                    continue
                if not line.strip():
                    if target_ip and scan_diff:
                        ip_id = db.select_id_by_ip(target_ip)
                        if ip_id != 0:
                            logging.info('   updating diffscan for {}...'.format(target_ip))
                            db.update_diff(ip_id, now, scan_diff)
                            total_updated += 1
                        else:
                            logging.warning(' ! host {} not found, cannot send diff !'.format(target_ip))
                    target_ip = ''
                    scan_diff = ''
                elif line.startswith('+') or line.startswith('-'):
                    scan_diff += line
                else:
                    if len(line.split()) == 1:
                        target_ip = line.strip().strip(':')
                    else:
                        target_ip = line.split()[1].strip('():')
        # last entry:
        if target_ip and scan_diff:
            ip_id = db.select_id_by_ip(target_ip)
            if ip_id != 0:
                logging.info('   updating diffscan for {}...'.format(target_ip))
                db.update_diff(ip_id, now, scan_diff)
                total_updated += 1
            else:
                logging.warning(' ! host {} not found, cannot send diff !'.format(target_ip))
        db.dbcommit()
        logging.info('\n*** Hosts changed: {}'.format(total_updated))

db.dbclose()
logging.info('\n*** Finished: {}\n'.format(datetime.datetime.now()))
